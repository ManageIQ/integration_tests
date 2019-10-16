from collections import defaultdict
from distutils.version import LooseVersion

import attr
import pytest
from cached_property import cached_property

from cfme.markers.env import EnvironmentMarker
from cfme.utils import conf
from cfme.utils.log import logger
from cfme.utils.providers import all_types
from cfme.utils.providers import list_providers
from cfme.utils.providers import ProviderFilter
from cfme.utils.pytest_shortcuts import fixture_filter
from cfme.utils.version import Version

ONE = 'one'
SECOND = 'second'
ALL = 'all'
LATEST = 'latest'
ONE_PER_VERSION = 'one_per_version'
ONE_PER_CATEGORY = 'one_per_category'
ONE_PER_TYPE = 'one_per_type'


class DPFilter(ProviderFilter):
    def __call__(self, provider):
        """ Applies this filter on a given DataProvider

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
            providers = list_providers([pf, pf_inverted])
            ^ this will return providers that have both the "openstack" and "complete" tags set
              and at the same time don't have the "disabled" tag
            ...or...
            pf = ProviderFilter(keys=['rhevm34'], class=CloudProvider, conjunctive=False)
            providers = list_providers([pf])
            ^ this will list all providers that either have the 'rhevm34' key or are an instance
              of the CloudProvider class and therefore are a cloud provider

        Returns:
            `True` if provider passed all checks and was not filtered out, `False` otherwise.
            The result is opposite if the 'inverted' attribute is set to `True`.
        """
        classes_l = self._filter_classes(provider)
        results = [classes_l]
        if not provider.one_of(DataProvider):
            from cfme.common.provider import BaseProvider
            if provider.one_of(BaseProvider):
                if self.required_fields:
                    results.append(self._filter_required_fields(provider))
                if self.required_tags:
                    results.append(self._filter_required_tags(provider))
                if self.required_flags:
                    results.append(self._filter_required_flags(provider))
        relevant_results = [res for res in results if res in [True, False]]
        compiling_fn = all if self.conjunctive else any
        # If all / any filters return true, the provider was not blocked (unless inverted)
        if compiling_fn(relevant_results):
            return not self.inverted
        return self.inverted

    def _filter_classes(self, provider):
        """ Filters by provider (base) classes """
        if self.classes is None:
            return None
        return any([prov_class in all_types()[provider.type_name].__mro__
                    for prov_class in self.classes])


def _param_check(metafunc, argnames, argvalues):
    """Helper function to check if parametrizing is necessary

    * If no argnames were specified, parametrization is unnecessary.
    * If argvalues were generated, parametrization is necessary.
    * If argnames were specified, but no values were generated, the test cannot run successfully,
      and will be uncollected using the :py:mod:`markers.uncollect` mark.

    See usage in :py:func:`parametrize`

    Args:
        metafunc: metafunc objects from pytest_generate_tests
        argnames: argnames list for use in metafunc.parametrize
        argvalues: argvalues list for use in metafunc.parametrize

    Returns:
        * ``True`` if this test should be parametrized
        * ``False`` if it shouldn't be parametrized
        * ``None`` if the test will be uncollected

    """
    assert isinstance(argvalues, list), "iterators break pytest expectations"
    # If no parametrized args were named, don't parametrize
    if not argnames:
        return False
    # If parametrized args were named and values were generated, parametrize
    elif any(argvalues):
        return True
    # If parametrized args were named, but no values were generated, mark this test to be
    # removed from the test collection. Otherwise, py.test will try to find values for the
    # items in argnames by looking in its fixture pool, which will almost certainly fail.
    else:
        # module and class are optional, but function isn't
        modname = getattr(metafunc.module, '__name__', None)
        classname = getattr(metafunc.cls, '__name__', None)
        funcname = metafunc.function.__name__

        test_name = '.'.join([_f for _f in (modname, classname, funcname) if _f])
        uncollect_msg = 'Parametrization for {} yielded no values,'\
            ' marked for uncollection'.format(test_name)
        logger.warning(uncollect_msg)

        # apply the mark
        pytest.mark.uncollect(reason=uncollect_msg)(metafunc.function)


def parametrize(metafunc, argnames, argvalues, *args, **kwargs):
    """parametrize wrapper that calls :py:func:`_param_check`, and only parametrizes when needed

    This can be used in any place where conditional parametrization is used.

    """
    kwargs.pop('selector')
    if _param_check(metafunc, argnames, argvalues):
        metafunc.parametrize(argnames, argvalues, *args, **kwargs)
    # if param check failed and the test was supposed to be parametrized around a provider
    elif 'provider' in metafunc.fixturenames:
        try:
            # hack to pass trough in case of a failed param_check
            # where it sets a custom message
            metafunc.function.uncollect
        except AttributeError:
            pytest.mark.uncollect(
                reason="provider was not parametrized did you forget --use-provider?"
            )(metafunc.function)


def data_provider_types(provider):
    return all_types()[provider.type_name]


@attr.s
class DataProvider(object):
    """A simple holder for a pseudo provider.

    This is not a real provider. This is used in place of a real provider to allow things like
    uncollections to take place in the case that we do not actually have an environment set up
    for this particular provider.
    """
    category = attr.ib()
    type_name = attr.ib()
    version = attr.ib()
    klass = attr.ib(default=attr.Factory(data_provider_types, takes_self=True))

    @cached_property
    def the_id(self):
        if self.version:
            return "{}-{}".format(self.type_name, self.version)
        else:
            return "{}".format(self.type_name)

    def one_of(self, *classes):
        return issubclass(self.klass, classes)

    def __repr__(self):
        return '{}({})[{}]'.format(self.type_name, self.category, self.version)


def all_required(miq_version, filters=None):
    """This returns a list DataProvider objects

    This list of providers is a representative of the providers that a test should be run against.

    Args:
        miq_version: The version of miq to query the supportability
        filters: A list of filters
    """
    # Load the supportability YAML and extrace the providers portion
    filters = filters or []  # default immutable
    stream = Version(miq_version).series()
    try:
        data_for_stream = conf.supportability[stream]['providers']
    except KeyError:
        logger.warning(f"A KeyError was caught while accessing supportability for {stream}")
        # there are cases when such data isn't available. For instance travis
        data_for_stream = {}

    # Build up a list of tuples in the form of category, type dictionary,
    #  [('cloud', {'openstack': [8, 9, 10]}), ('cloud', {'ec2'})]
    types = [
        (cat, type)
        for cat, types in data_for_stream.items()
        for type in types
    ]

    # Build up a list of data providers by iterating the types list from above
    dprovs = []
    for cat, prov_type_or_dict in types:
        if isinstance(prov_type_or_dict, str):
            # If the provider is versionless, ie, EC2, GCE, set the version number to 0
            dprovs.append(DataProvider(cat, prov_type_or_dict, 0))
        else:
            # If the prov_type_or_dict is not just a string, then we have versions and need
            # to iterate and extend the list
            dprovs.extend([
                DataProvider(cat, prov, ver)
                for prov, vers in prov_type_or_dict.items()
                for ver in vers
            ])

    nfilters = [DPFilter(classes=pf.classes, inverted=pf.inverted)
                for pf in filters if isinstance(pf, ProviderFilter)]
    for prov_filter in nfilters:
        dprovs = list(filter(prov_filter, dprovs))
    return dprovs


def providers(metafunc, filters=None, selector=ALL, fixture_name='provider'):
    """ Gets providers based on given (+ global) filters

    Note:
        Using the default 'function' scope, each test will be run individually for each provider
        before moving on to the next test. To group all tests related to single provider together,
        parametrize tests in the 'module' scope.

    Note:
        testgen for providers now requires the usage of test_flags for collection to work.
        Please visit http://cfme-tests.readthedocs.org/guides/documenting.html#documenting-tests
        for more details.
    """
    filters = filters or []
    argnames = []
    argvalues = []
    idlist = []

    # Obtains the test's flags in form of a ProviderFilter
    meta = getattr(metafunc.function, 'meta', None)
    test_flag_str = getattr(meta, 'kwargs', {}).get('from_docs', {}).get('test_flag')
    if test_flag_str:
        test_flags = test_flag_str.split(',')
        flags_filter = ProviderFilter(required_flags=test_flags)
        filters = filters + [flags_filter]

    # available_providers are the ones "available" from the yamls after all of the global and
    # local filters have been applied. It will be a list of crud objects.
    available_providers = list_providers(filters)

    # supported_providers are the ones "supported" in the supportability.yaml file. It will
    # be a list of DataProvider objects and will be filtered based upon what the test has asked for
    holder = metafunc.config.pluginmanager.get_plugin('appliance-holder')
    series = holder.held_appliance.version.series()
    supported_providers = all_required(series, filters)

    def get_valid_providers(provider):
        # We now search through all the available providers looking for one that matches the
        # criteria. If we don't find one, we return None
        prov_tuples = []
        for a_prov in available_providers:
            try:
                if not a_prov.version:
                    raise ValueError("provider {p} has no version".format(p=a_prov))
                elif (a_prov.version == provider.version and
                        a_prov.type == provider.type_name and
                        a_prov.category == provider.category):
                    prov_tuples.append((provider, a_prov))
            except (KeyError, ValueError):
                if (a_prov.type == provider.type_name and
                        a_prov.category == provider.category):
                    prov_tuples.append((provider, a_prov))
        return prov_tuples

    # A small routine to check if we need to supply the idlist a provider type or
    # a real type/version
    need_prov_keys = False
    for filter in filters:
        if isinstance(filter, ProviderFilter) and filter.classes:
            for filt in filter.classes:
                if hasattr(filt, 'type_name'):
                    need_prov_keys = True
                    break

    matching_provs = [valid_provider
                      for prov in supported_providers
                      for valid_provider in get_valid_providers(prov)]

    # Now we run through the selectors and build up a list of supported providers which match our
    # requirements. This then forms the providers that the test should run against.
    if selector == ONE:
        if matching_provs:
            allowed_providers = [matching_provs[0]]
        else:
            allowed_providers = []
    elif selector == SECOND:
        if matching_provs:
            try:
                allowed_providers = [matching_provs[1]]
            except IndexError:
                pytest.skip("no second provider was found")
        else:
            allowed_providers = []
    elif selector == LATEST:
        allowed_providers = [sorted(
            matching_provs, key=lambda k:LooseVersion(
                str(k[0].version)), reverse=True
        )[0]]
    elif selector == ONE_PER_TYPE:
        types = set()

        def add_prov(prov):
            types.add(prov[0].type_name)
            return prov

        allowed_providers = [
            add_prov(prov) for prov in matching_provs if prov[0].type_name not in types
        ]
    elif selector == ONE_PER_CATEGORY:
        categories = set()

        def add_prov(prov):
            categories.add(prov[0].category)
            return prov

        allowed_providers = [
            add_prov(prov) for prov in matching_provs if prov[0].category not in categories
        ]
    elif selector == ONE_PER_VERSION:
        # This needs to handle versions per type
        versions = defaultdict(set)

        def add_prov(prov):
            versions[prov[0].type_name].add(prov[0].version)
            return prov

        allowed_providers = [
            add_prov(prov)
            for prov in matching_provs
            if prov[0].version not in versions[prov[0].type_name]
        ]
    else:
        # If there are no selectors, then the allowed providers are whichever are supported
        allowed_providers = matching_provs

    # Now we iterate through the required providers and try to match them to the available ones
    for data_prov, real_prov in allowed_providers:
        data_prov.key = real_prov.key
        argvalues.append(pytest.param(data_prov))

        # Use the provider key for idlist, helps with readable parametrized test output
        the_id = str(data_prov.key) if metafunc.config.getoption('legacy_ids') else data_prov.the_id

        # Now we modify the id based on what selector we chose
        if metafunc.config.getoption('disable_selectors'):
            idlist.append(the_id)
        else:
            if selector == ONE:
                if need_prov_keys:
                    idlist.append(data_prov.type_name)
                else:
                    idlist.append(data_prov.category)
            elif selector == ONE_PER_CATEGORY:
                idlist.append(data_prov.category)
            elif selector == ONE_PER_TYPE:
                idlist.append(data_prov.type_name)
            else:
                idlist.append(the_id)

        # Add provider to argnames if missing
        if fixture_name in metafunc.fixturenames and fixture_name not in argnames:
            metafunc.function = pytest.mark.uses_testgen()(metafunc.function)
            argnames.append(fixture_name)
        if metafunc.config.getoption('sauce') or selector == ONE:
            break
    return argnames, argvalues, idlist


def providers_by_class(
        metafunc, classes, required_fields=None, selector=ALL, fixture_name='provider',
        required_flags=None):
    """ Gets providers by their class

    Args:
        metafunc: Passed in by pytest
        classes: List of classes to fetch
        required_fields: See :py:class:`cfme.utils.provider.ProviderFilter`

    Usage:
        # In the function itself
        def pytest_generate_tests(metafunc):
            argnames, argvalues, idlist = testgen.providers_by_class(
                [GCEProvider, AzureProvider], required_fields=['provisioning']
            )
        metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')

        # Using the parametrize wrapper
        pytest_generate_tests = testgen.parametrize([GCEProvider], scope='module')
    """
    pf = DPFilter(classes=classes, required_fields=required_fields, required_flags=required_flags)
    return providers(metafunc, filters=[pf], selector=selector, fixture_name=fixture_name)


class ProviderEnvironmentMarker(EnvironmentMarker):
    NAME = 'provider'

    def process_env_mark(self, metafunc):
        if hasattr(metafunc.function, self.NAME):
            mark_dict = defaultdict(list)
            for mark in getattr(metafunc.function, self.NAME):
                # Find all provider-ish markers
                fixture_name = mark.kwargs.get('fixture_name', 'provider')
                mark_dict[fixture_name].append(mark)

            for name, marks in mark_dict.items():
                mark = None
                for mark in marks:
                    if mark.kwargs.get('override', False):
                        break
                else:
                    if len(mark_dict[name]) >= 2:
                        raise Exception(
                            "You have an override provider without "
                            "specifying the override flag [{}]".format(metafunc.function.__name__)
                        )

                args = mark.args
                kwargs = mark.kwargs.copy()
                if 'override' in kwargs:
                    kwargs.pop('override')
                scope = kwargs.pop('scope', 'function')
                indirect = kwargs.pop('indirect', False)
                filter_unused = kwargs.pop('filter_unused', True)
                selector = kwargs.pop('selector', ALL)
                gen_func = kwargs.pop('gen_func', providers_by_class)

                # If parametrize doesn't get you what you need, steal this and modify as needed
                kwargs.update({'selector': selector})
                argnames, argvalues, idlist = gen_func(metafunc, *args, **kwargs)
                # Filter out argnames that aren't requested on the metafunc test item,
                # so not all tests need all fixtures to run, and tests not using gen_func's
                # fixtures aren't parametrized.
                if filter_unused:
                    argnames, argvalues = fixture_filter(metafunc, argnames, argvalues)
                    # See if we have to parametrize at all after filtering
                parametrize(
                    metafunc, argnames, argvalues, indirect=indirect,
                    ids=idlist, scope=scope, selector=selector
                )
