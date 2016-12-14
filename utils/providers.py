""" Helper functions related to the creation, listing, filtering and destruction of providers

The functions in this module that require the 'filters' parameter, such as list_providers,
setup_a_provider etc depend on a (by default global) dict of filters by default.
If you are writing tests or fixtures, you want to depend on those functions as de facto gateways.

The rest of the functions, such as get_mgmt, get_crud etc ignore this global dict and will provide
you with whatever you ask for with no limitations.

The main clue to know what is limited by the filters and what isn't is the 'filters' parameter.
"""
import operator
import random
import six
from collections import Mapping, OrderedDict
from copy import copy

from fixtures.pytest_store import store
from cfme.common.provider import BaseProvider

from cfme.containers import provider as containers_providers # NOQA
from cfme.cloud import provider as cloud_providers # NOQA
from cfme.infrastructure import provider as infrastructure_providers # NOQA
from cfme.middleware import provider as middleware_providers # NOQA

from cfme.exceptions import UnknownProviderType
from cfme.infrastructure.provider import InfraProvider
from utils import conf, version
from utils.log import logger

providers_data = conf.cfme_data.get("management_systems", {})
# Dict of active provider filters {name: ProviderFilter}
global_filters = {}


class ProviderFilter(object):
    """ Filter used to obtain only providers matching given requirements

    Args:
        keys: List of acceptable provider keys, all if `None`
        categories: List of acceptable provider categories, all if `None`
        types: List of acceptable provider types, all if `None`
        required_fields: List of required fields, see :py:func:`providers_by_class`
        restrict_version: Checks provider version in yamls if `True`
        required_tags: List of tags that must be set in yamls
        inverted: Inclusive if `False`, exclusive otherwise
        conjunctive: If true, all subfilters are applied and all must match (default)
                     If false (disjunctive), at least one of the subfilters must match
    """
    _version_operator_map = OrderedDict([('>=', operator.ge),
                                        ('<=', operator.le),
                                        ('==', operator.eq),
                                        ('!=', operator.ne),
                                        ('>', operator.gt),
                                        ('<', operator.lt)])

    def __init__(self, keys=None, classes=None, required_fields=None, required_tags=None,
                 required_flags=None, restrict_version=False, inverted=False, conjunctive=True):
        self.keys = keys
        self.classes = classes
        self.required_fields = required_fields
        self.required_tags = required_tags
        self.required_flags = required_flags
        self.restrict_version = restrict_version
        self.inverted = inverted
        self.conjunctive = conjunctive

    def _filter_keys(self, provider):
        """ Filters by provider keys """
        if self.keys is None:
            return None
        return provider.key in self.keys

    def _filter_classes(self, provider):
        """ Filters by provider (base) classes """
        if self.classes is None:
            return None
        return any([provider.one_of(prov_class) for prov_class in self.classes])

    def _filter_required_fields(self, provider):
        """ Filters by required yaml fields (specified usually during test parametrization) """
        if self.required_fields is None:
            return None
        for field_or_fields in self.required_fields:
            if isinstance(field_or_fields, tuple):
                field_ident, field_value = field_or_fields
            else:
                field_ident, field_value = field_or_fields, None
            if isinstance(field_ident, six.string_types):
                if field_ident not in provider.data:
                    return False
                else:
                    if field_value:
                        if provider.data[field_ident] != field_value:
                            return False
            else:
                o = provider.data
                try:
                    for field in field_ident:
                        o = o[field]
                    if field_value:
                        if o != field_value:
                            return False
                except (IndexError, KeyError):
                    return False
        return True

    def _filter_required_tags(self, provider):
        """ Filters by required yaml tags """
        prov_tags = provider.data.get('tags', [])
        if self.required_tags is None:
            return None
        if set(self.required_tags) & set(prov_tags):
            return True
        return False

    def _filter_required_flags(self, provider):
        """ Filters by required yaml flags """
        if self.required_flags is None:
            return None
        if self.required_flags:
            test_flags = [flag.strip() for flag in self.required_flags]

            defined_flags = conf.cfme_data.get('test_flags', '').split(',')
            defined_flags = [flag.strip() for flag in defined_flags]

            excluded_flags = provider.data.get('excluded_test_flags', '').split(',')
            excluded_flags = [flag.strip() for flag in excluded_flags]

            allowed_flags = set(defined_flags) - set(excluded_flags)

            if set(test_flags) - allowed_flags:
                logger.info("Filtering Provider %s out because it does not have the right flags, "
                            "%s does not contain %s",
                            provider.name, list(allowed_flags),
                            list(set(test_flags) - allowed_flags))
                return False
        return True

    def _filter_restricted_version(self, provider):
        """ Filters by yaml version restriction; not applied if SSH is not available """
        if self.restrict_version:
            # TODO
            # get rid of this since_version hotfix by translating since_version
            # to restricted_version; in addition, restricted_version should turn into
            # "version_restrictions" and it should be a sequence of restrictions with operators
            # so that we can create ranges like ">= 5.6" and "<= 5.8"
            version_restrictions = []
            since_version = provider.data.get('since_version', None)
            if since_version:
                version_restrictions.append('>= {}'.format(since_version))
            restricted_version = provider.data.get('restricted_version', None)
            if restricted_version:
                version_restrictions.append(restricted_version)
            for restriction in version_restrictions:
                for op, comparator in ProviderFilter._version_operator_map.items():
                    # split string by op; if the split works, version won't be empty
                    head, op, ver = restriction.partition(op)
                    if not ver:  # This means that the operator was not found
                        continue
                    try:
                        curr_ver = version.current_version()
                    except:
                        return True
                    if not comparator(curr_ver, ver):
                        return False
                    break
                else:
                    raise Exception('Operator not found in {}'.format(restriction))
        return None

    def __call__(self, provider):
        """ Applies this filter on a given provider

        Usage:
            pf = ProviderFilter('cloud_infra', categories=['cloud', 'infra'])
            providers = list_providers([pf])
            pf2 = ProviderFilter(
                classes=[GCEProvider, EC2Provider], required_fields=['small_template'])
            provider_keys = [prov.key for prov in list_providers([pf, pf2])]
            ^ this will list keys of all GCE and EC2 providers
            ...or...
            pf = ProviderFilter(required_tags=['openstack', 'complete'])
            pf_inverted = ProviderFilter(required_tags=['disabled'], inverted=True)
            provider = new_setup_a_provider([pf, pf_inverted])
            ^ this will setup a provider that has both the "openstack" and "complete" tags set
              and at the same time does not have the "disabled" tag
            ...or...
            pf = ProviderFilter(keys=['rhevm34'], class=CloudProvider, conjunctive=False)
            providers = list_providers([pf])
            ^ this will list all providers that either have the 'rhevm34' key or are an instance
              of the CloudProvider class and therefore are a cloud provider

        Returns:
            `True` if provider passed all checks and was not filtered out, `False` otherwise.
            The result is opposite if the 'inverted' attribute is set to `True`.
        """
        keys_l = self._filter_keys(provider)
        classes_l = self._filter_classes(provider)
        fields_l = self._filter_required_fields(provider)
        tags_l = self._filter_required_tags(provider)
        flags_l = self._filter_required_flags(provider)
        version_l = self._filter_restricted_version(provider)
        results = [keys_l, classes_l, fields_l, tags_l, flags_l, version_l]
        relevant_results = [res for res in results if res in [True, False]]
        compiling_fn = all if self.conjunctive else any
        # If all / any filters return true, the provider was not blocked (unless inverted)
        if compiling_fn(relevant_results):
            return not self.inverted
        return self.inverted

    def copy(self):
        return copy(self)


# Only providers without the 'disabled' tag
global_filters['enabled_only'] = ProviderFilter(required_tags=['disabled'], inverted=True)
# Only providers relevant for current appliance version (requires SSH access when used)
global_filters['restrict_version'] = ProviderFilter(restrict_version=True)


def list_providers(filters=None, use_global_filters=True):
    """ Lists provider crud objects, global filter optional

    Args:
        filters: List if :py:class:`ProviderFilter` or None
        use_global_filters: Will apply global filters as well if `True`, will not otherwise

    Note: Requires the framework to be pointed at an appliance to succeed.

    Returns: List of provider crud objects.
    """
    filters = filters or []
    if use_global_filters:
        filters = filters + global_filters.values()
    providers = [get_crud(prov_key) for prov_key in providers_data]
    for prov_filter in filters:
        providers = filter(prov_filter, providers)
    return providers


def list_providers_by_class(prov_class, use_global_filters=True):
    """ Lists provider crud objects of a specific class (or its subclasses), global filter optional

    Args:
        prov_class: Provider class to apply for filtering
        use_global_filters: See :py:func:`list_providers`

    Note: Requires the framework to be pointed at an appliance to succeed.

    Returns: List of provider crud objects.
    """
    pf = ProviderFilter(classes=[prov_class])
    return list_providers(filters=[pf], use_global_filters=use_global_filters)


def list_provider_keys(provider_type=None):
    """ Lists provider keys from conf (yamls)

    Args:
        provider_type: Optional filtering by 'type' string (from yaml); disabled by default

    Note: Doesn't require the framework to be pointed at an appliance to succeed.

    Returns: List of provider keys (strings).
    """
    try:
        all_keys = conf.cfme_data.management_systems.keys()
    except:
        all_keys = []

    if provider_type:
        filtered_keys = []
        for key in all_keys:
            if conf.cfme_data.management_systems[key].type == provider_type:
                filtered_keys.append(key)
        return filtered_keys
    else:
        return all_keys


def setup_provider(provider_key, validate=True, check_existing=True):
    provider = get_crud(provider_key)
    provider.create(validate_credentials=True, validate_inventory=validate,
                    check_existing=check_existing)
    return provider


def new_setup_a_provider(filters=None, use_global_filters=True, validate=True, check_existing=True):
    """ Sets up a single provider robustly.

    Does some counter-badness measures.

    Args:
        filters: List if :py:class:`ProviderFilter` or None; infra providers by default
        use_global_filters: Will apply global filters as well if `True`, will not otherwise
        validate: Whether to validate the provider.
        check_existing: Whether to check if the provider already exists.
    """
    filters = filters or []

    providers = list_providers(filters=filters, use_global_filters=use_global_filters)
    if not providers:
        raise Exception("All providers have been filtered out, cannot setup any providers")

    # If there is a provider already set up matching the user's requirements, reuse it
    for provider in providers:
        if provider.exists:
            return provider

    # Activate the 'nonproblematic' filter to filter out problematic providers (if any)
    if global_filters.get('problematic') is None:
        global_filters['problematic'] = ProviderFilter(keys=[], inverted=True)

    # If there are no non-problematic providers, reset the filter
    nonproblematic_providers = list_providers(filters=filters)
    if not nonproblematic_providers:
        global_filters['problematic'].keys = []
        store.terminalreporter.write_line(
            "Reached the point where all possible providers forthis case are marked as bad. "
            "Clearing the bad provider list for a fresh start and next chance.", yellow=True)
    # Otherwise, make non-problematic the new cool
    else:
        providers = nonproblematic_providers

    # If we have more than one provider, try to pick one that doesnt have the do_not_prefer flag set
    if len(providers) > 1:
        do_not_prefer_filter = ProviderFilter(required_fields=[("do_not_prefer", False)],
                                              inverted=True)
        # If we find any providers without the 'do_not_prefer' flag, add  the filter to the list
        # of active filters and make preferred providers the new cool
        preferred_providers = list_providers(filters=filters + [do_not_prefer_filter])
        if preferred_providers:
            filters.append(do_not_prefer_filter)
            providers = preferred_providers

    # Try to set up a nonexisting provider (return if successful, otherwise try another)
    non_existing = [prov for prov in providers if not prov.exists]
    random.shuffle(non_existing)  # Make the provider load even (long-term) by shuffling them around
    for provider in non_existing:
        try:
            store.terminalreporter.write_line(
                "Trying to set up provider {}\n".format(provider.key), green=True)
            provider.create(validate_credentials=True, validate_inventory=validate,
                            check_existing=check_existing)
            return provider
        except Exception as e:
            # In case of a known provider error:
            logger.exception(e)
            message = "Provider {} is behaving badly, marking it as bad. {}: {}".format(
                provider.key, type(e).__name__, str(e))
            logger.warning(message)
            store.terminalreporter.write_line(message + "\n", red=True)
            global_filters['problematic'].keys.append(provider.key)
            if provider.exists:
                # Remove it in order to not explode on next calls
                provider.delete(cancel=False)
                provider.wait_for_delete()
                message = "Provider {} was deleted because it failed to set up.".format(
                    provider.key)
                logger.warning(message)
                store.terminalreporter.write_line(message + "\n", red=True)
    else:
        raise Exception("No providers could be set up matching the params")

    return provider


def setup_a_provider_by_class(prov_class=InfraProvider, validate=True, check_existing=True):
    pf = ProviderFilter(classes=[prov_class])
    return new_setup_a_provider(filters=[pf], validate=validate, check_existing=check_existing)


# Replaced by setup_a_provider_by_class
def setup_a_provider(prov_class="infra", prov_type=None, validate=True, check_existing=True):
    prov_class = get_class_from_type(prov_type or prov_class)
    return setup_a_provider_by_class(
        prov_class=prov_class, validate=validate, check_existing=check_existing)


def get_class_from_type(prov_type):
    """ Serves to translate both provider types and categories to actual classes """
    all_classes_map = BaseProvider.base_types.copy()
    for base_type in BaseProvider.base_types.itervalues():
        all_classes_map.update(base_type.provider_types)
    try:
        return all_classes_map[prov_type]
    except KeyError:
        raise UnknownProviderType("Unknown provider type: {}!".format(prov_type))


def get_crud(provider_key):
    """ Creates a Provider object given a management_system key in cfme_data.

    Usage:
        get_crud('ec2east')

    Returns: A Provider object that has methods that operate on CFME
    """
    prov_config = providers_data[provider_key]
    prov_type = prov_config.get('type')

    return get_class_from_type(prov_type).from_config(prov_config, provider_key)


def get_crud_by_name(provider_name):
    """ Creates a Provider object given a management_system name in cfme_data.

    Usage:
        get_crud_by_name('My RHEV 3.6 Provider')

    Returns: A Provider object that has methods that operate on CFME
    """
    for provider_key, provider_data in providers_data.items():
        if provider_data.get("name") == provider_name:
            return get_crud(provider_key)
    raise NameError("Could not find provider {}".format(provider_name))


def get_mgmt(provider_key, providers=None, credentials=None):
    """ Provides a ``mgmtsystem`` object, based on the request.

    Args:
        provider_key: The name of a provider, as supplied in the yaml configuration files.
            You can also use the dictionary if you want to pass the provider data directly.
        providers: A set of data in the same format as the ``management_systems`` section in the
            configuration yamls. If ``None`` then the configuration is loaded from the default
            locations. Expects a dict.
        credentials: A set of credentials in the same format as the ``credentials`` yamls files.
            If ``None`` then credentials are loaded from the default locations. Expects a dict.
    Return: A provider instance of the appropriate ``mgmtsystem.MgmtSystemAPIBase``
        subclass
    """
    if providers is None:
        providers = providers_data
    # provider_key can also be provider_data for some reason
    # TODO rename the parameter; might break things
    if isinstance(provider_key, Mapping):
        provider_data = provider_key
    else:
        provider_data = providers[provider_key]

    if credentials is None:
        # We need to handle the in-place credentials
        credentials = provider_data['credentials']
        # If it is not a mapping, it most likely points to a credentials yaml (as by default)
        if not isinstance(credentials, Mapping):
            credentials = conf.credentials[credentials]
        # Otherwise it is a mapping and therefore we consider it credentials

    # Munge together provider dict and creds,
    # Let the provider do whatever they need with them
    provider_kwargs = provider_data.copy()
    provider_kwargs.update(credentials)
    if isinstance(provider_key, six.string_types):
        provider_kwargs['provider_key'] = provider_key
    provider_kwargs['logger'] = logger

    return get_class_from_type(provider_data['type']).mgmt_class(**provider_kwargs)


class UnknownProvider(Exception):
    def __init__(self, provider_key, *args, **kwargs):
        super(UnknownProvider, self).__init__(provider_key, *args, **kwargs)
        self.provider_key = provider_key

    def __str__(self):
        return ('Unknown provider: "{}"'.format(self.provider_key))
