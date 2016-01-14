"""Helper functions related to the creation and destruction of providers

To quickly add all providers::

    setup_providers(validate=False)

"""
import random
from collections import Mapping
from functools import partial
from operator import methodcaller

import cfme.fixtures.pytest_selenium as sel
from fixtures.pytest_store import store
from cfme.web_ui import Quadicon, paginator, toolbar
from cfme.common.provider import BaseProvider
from cfme.exceptions import UnknownProviderType
from cfme.containers.provider import KubernetesProvider, OpenshiftProvider
from cfme.infrastructure.provider import (
    OpenstackInfraProvider, RHEVMProvider, VMwareProvider, SCVMMProvider)
from fixtures.prov_filter import filtered
from utils import conf, mgmt_system, version
from utils.log import logger, perflog
from utils.wait import wait_for

#: mapping of infra provider type names to :py:mod:`utils.mgmt_system` classes
infra_provider_type_map = {
    'virtualcenter': mgmt_system.VMWareSystem,
    'rhevm': mgmt_system.RHEVMSystem,
    'scvmm': mgmt_system.SCVMMSystem,
    'openstack-infra': mgmt_system.OpenstackInfraSystem,
}

#: mapping of cloud provider type names to :py:mod:`utils.mgmt_system` classes
cloud_provider_type_map = {
    'ec2': mgmt_system.EC2System,
    'openstack': mgmt_system.OpenstackSystem,
}

#: mapping of container provider type names to :py:mod:`utils.mgmt_system` classes
container_provider_type_map = {
    'kubernetes': mgmt_system.Kubernetes,
    'openshift': mgmt_system.Openshift
}

#: mapping of all provider type names to :py:mod:`utils.mgmt_system` classes
provider_type_map = dict(
    infra_provider_type_map.items()
    + cloud_provider_type_map.items()
    + container_provider_type_map.items()
)

providers_data = conf.cfme_data.get("management_systems", {})

# This is a global variable. Not the most ideal way to do things but how can we track bad providers?
problematic_providers = set([])


def list_providers(allowed_types):
    """ Returns list of providers of selected type from configuration.

    @param allowed_types: Passed by partial(), see top of this file.
    @type allowed_types: dict, list, set, tuple
    """
    providers = []
    for provider, data in providers_data.items():
        provider_type = data.get("type", None)
        if provider not in filtered:
            continue
        assert provider_type is not None, "Provider %s has no type specified!" % provider
        if provider_type in allowed_types:
            providers.append(provider)
    return providers

#: function that returns a list of infra provider keys in cfme_data
list_infra_providers = partial(list_providers, infra_provider_type_map.keys())

#: function that returns a list of cloud provider keys in cfme_data
list_cloud_providers = partial(list_providers, cloud_provider_type_map.keys())

#: function that returns a list of container provider keys in cfme_data
list_container_providers = partial(list_providers, container_provider_type_map.keys())

#: function that returns a list of all provider keys in cfme_data
list_all_providers = partial(list_providers, provider_type_map.keys())


def is_cloud_provider(provider_key):
    return provider_key in list_cloud_providers()


def is_infra_provider(provider_key):
    return provider_key in list_infra_providers()


def is_container_provider(provider_key):
    return provider_key in list_container_providers()


def get_mgmt(provider_key, providers=None, credentials=None):
    """
    Provides a :py:mod:`utils.mgmt_system` object, based on the request.

    Args:
        provider_key: The name of a provider, as supplied in the yaml configuration files.
            You can also use the dictionary if you want to pass the provider data directly.
        providers: A set of data in the same format as the ``management_systems`` section in the
            configuration yamls. If ``None`` then the configuration is loaded from the default
            locations. Expects a dict.
        credentials: A set of credentials in the same format as the ``credentials`` yamls files.
            If ``None`` then credentials are loaded from the default locations. Expects a dict.
    Return: A provider instance of the appropriate :py:class:`utils.mgmt_system.MgmtSystemAPIBase`
        subclass
    """
    if providers is None:
        providers = providers_data
    if isinstance(provider_key, Mapping):
        provider = provider_key
    else:
        provider = providers[provider_key]

    if credentials is None:
        credentials = conf.credentials[provider['credentials']]

    # Munge together provider dict and creds,
    # Let the provider do whatever they need with them
    provider_kwargs = provider.copy()
    provider_kwargs.update(credentials)
    if isinstance(provider_key, basestring):
        provider_kwargs['provider_key'] = provider_key
    provider_kwargs['logger'] = logger
    provider_instance = provider_type_map[provider['type']](**provider_kwargs)
    return provider_instance


def get_provider_key(provider_name):
    for provider_key, provider_data in providers_data.items():
        if provider_data.get("name") == provider_name:
            return provider_key
    else:
        raise NameError("Could not find provider {}".format(provider_name))


def get_mgmt_by_name(provider_name, *args, **kwargs):
    """Provides a :py:mod:`utils.mgmt_system` object, based on the request.

    For detailed parameter description, refer to the :py:func:`get_mgmt` (except its
    `provider_key` parameter)

    Args:
        provider_name: 'Nice' provider name (name field from provider's YAML entry)
    Return: A provider instance of the appropriate :py:class:`utils.mgmt_system.MgmtSystemAPIBase`
        subclass
    """
    return get_mgmt(get_provider_key(provider_name), *args, **kwargs)


def setup_a_provider(prov_class=None, prov_type=None, validate=True, check_existing=True,
                     required_keys=None):
    """Sets up a single provider robustly.

    Does some counter-badness measures.

    Args:
        prov_class: "infra", "cloud" or "container"
        prov_type: "ec2", "virtualcenter" or any other valid type
        validate: Whether to validate the provider.
        check_existing: Whether to check if the provider already exists.
        required_keys: A set of required keys for the provider data to have
    """
    if not required_keys:
        required_keys = []
    if prov_class in ("infra", "cloud", "container"):
        if prov_class == "infra":
            potential_providers = list_infra_providers()
        elif prov_class == "cloud":
            potential_providers = list_cloud_providers()
        else:
            potential_providers = list_container_providers()
        if prov_type:
            providers = []
            for provider in potential_providers:
                if providers_data[provider]['type'] == prov_type:
                    providers.append(provider)
        else:
            providers = potential_providers
    else:
        providers = list_infra_providers()

    final_providers = []
    for provider in providers:
        if all(key in providers_data[provider] for key in required_keys):
            final_providers.append(provider)
    providers = final_providers

    # Check if the provider was behaving badly in the history
    if problematic_providers:
        filtered_providers = [
            provider for provider in providers if provider not in problematic_providers]
        if not filtered_providers:
            # problematic_providers took all of the providers, so start over with clean list
            # (next chance for bad guys) and use the original list. This will then slow down a
            # little bit but make it more reliable.
            problematic_providers.clear()
            store.terminalreporter.write_line(
                "Reached the point where all possible providers forthis case are marked as bad. "
                "Clearing the bad provider list for a fresh start and next chance.", yellow=True)
        else:
            providers = filtered_providers

    # If there is a provider that we want to specifically avoid ...
    # If there is only a single provider, then do not do any filtering
    # Specify `do_not_prefer` in provider's yaml to make it an object of avoidance.
    if len(providers) > 1:
        filtered_providers = [
            provider
            for provider
            in providers
            if not providers_data[provider].get("do_not_prefer", False)]
        if filtered_providers:
            # If our filtering yielded any providers, use them, otherwise do not bother with that
            providers = filtered_providers

    # If there is already a suitable provider, don't try to setup a new one.
    already_existing = filter(is_provider_setup, providers)
    random.shuffle(already_existing)        # Make the provider load more even by random chaice.
    not_already_existing = filter(lambda x: not is_provider_setup(x), providers)
    random.shuffle(not_already_existing)    # Make the provider load more even by random chaice.

    # So, make this one loop and it tries the existing providers first, then the nonexisting
    for provider in already_existing + not_already_existing:
        try:
            if provider in already_existing:
                store.terminalreporter.write_line(
                    "Trying to reuse provider {}\n".format(provider), green=True)
            else:
                store.terminalreporter.write_line(
                    "Trying to set up provider {}\n".format(provider), green=True)
            return setup_provider(provider, validate=validate, check_existing=check_existing)
        except Exception as e:
            # In case of a known provider error:
            logger.exception(e)
            message = "Provider {} is behaving badly, marking it as bad. {}: {}".format(
                provider, type(e).__name__, str(e))
            logger.warning(message)
            store.terminalreporter.write_line(message + "\n", red=True)
            problematic_providers.add(provider)
            prov_object = get_crud(provider)
            if prov_object.exists:
                # Remove it in order to not explode on next calls
                prov_object.delete(cancel=False)
                prov_object.wait_for_delete()
                message = "Provider {} was deleted because it failed to set up.".format(provider)
                logger.warning(message)
                store.terminalreporter.write_line(message + "\n", red=True)
    else:
        raise Exception("No providers could be set up matching the params")


def is_provider_setup(provider_key):
    """Checks whether provider is already existing in CFME

    Args:
        provider_key: YAML key of the provider

    Returns:
        :py:class:`bool` of existence
    """
    return get_crud(provider_key).exists


def setup_provider(provider_key, validate=True, check_existing=True):
    """Add the named provider to CFME

    Args:
        provider_key: Provider key name from cfme_data
        validate: Whether or not to block until the provider stats in CFME
            match the stats gleaned from the backend management system
            (default: ``True``)
        check_existing: Check if this provider already exists, skip if it does

    Returns:
        An instance of :py:class:`cfme.cloud.provider.Provider` or
        :py:class:`cfme.infrastructure.provider.Provider` for the named provider, as appropriate.

    """
    provider = get_crud(provider_key)
    if check_existing and provider.exists:
        # no need to create provider if the provider exists
        # pass so we don't skip the validate step
        pass
    else:
        logger.info('Setting up provider: %s' % provider.key)
        provider.create(validate_credentials=True)

    if validate:
        provider.validate()

    return provider


def setup_provider_by_name(provider_name, *args, **kwargs):
    return setup_provider(get_provider_key(provider_name), *args, **kwargs)


def setup_providers(prov_classes=('cloud', 'infra'), validate=True, check_existing=True):
    """Run :py:func:`setup_provider` for every provider (cloud and infra only, by default)

    Args:
        prov_classes: list of provider classes to setup ('cloud', 'infra' and 'container')
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    Returns:
        A list of provider object for the created providers, cloud and infrastructure.

    """
    perflog.start('utils.providers.setup_providers')
    # Do cloud and infra separately to keep the browser navs down
    added_providers = []

    # Defer validation
    setup_kwargs = {'validate': False, 'check_existing': check_existing}
    if 'cloud' in prov_classes:
        added_providers.extend(setup_cloud_providers(**setup_kwargs))
    if 'infra' in prov_classes:
        added_providers.extend(setup_infrastructure_providers(**setup_kwargs))
    if 'container' in prov_classes:
        added_providers.extend(setup_container_providers(**setup_kwargs))

    if validate:
        map(methodcaller('validate'), added_providers)

    perflog.stop('utils.providers.setup_providers')

    return added_providers


def _setup_providers(prov_class, validate, check_existing):
    """Helper to set up all cloud, infra or container providers, and then validate them

    Args:
        prov_class: Provider class - 'cloud, 'infra' or 'container' (a string)
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    Returns:
        A list of provider objects that have been created.

    """
    # Pivot behavior on prov_class
    options_map = {
        'cloud': {
            'navigate': 'clouds_providers',
            'quad': 'cloud_prov',
            'list': list_cloud_providers
        },
        'infra': {
            'navigate': 'infrastructure_providers',
            'quad': 'infra_prov',
            'list': list_infra_providers
        },
        'container': {
            'navigate': 'container_providers',
            'quad': None,
            'list': list_container_providers
        }
    }
    # Check for existing providers all at once, to prevent reloading
    # the providers page for every provider in cfme_data
    if not options_map[prov_class]['list']():
        return []
    if check_existing:
        sel.force_navigate(options_map[prov_class]['navigate'])
        add_providers = []
        for provider_key in options_map[prov_class]['list']():
            provider_name = conf.cfme_data.get('management_systems', {})[provider_key]['name']
            quad = Quadicon(provider_name, options_map[prov_class]['quad'])
            for page in paginator.pages():
                if sel.is_displayed(quad):
                    logger.debug('Provider "%s" exists, skipping' % provider_key)
                    break
            else:
                add_providers.append(provider_key)
    else:
        # Add all cloud, infra or container providers unconditionally
        add_providers = options_map[prov_class]['list']()

    if add_providers:
        logger.info('Providers to be added: %s' % ', '.join(add_providers))

    # Save the provider objects for validation and return
    added_providers = []

    for provider_name in add_providers:
        # Don't validate in this step; add all providers, then go back and validate in order
        provider = setup_provider(provider_name, validate=False, check_existing=False)
        added_providers.append(provider)

    if validate:
        map(methodcaller('validate'), added_providers)

    return added_providers


def setup_cloud_providers(validate=True, check_existing=True):
    """Run :py:func:`setup_cloud_provider` for every cloud provider

    Args:
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    Returns:
        An list of :py:class:`cfme.cloud.provider.Provider` instances.

    """
    return _setup_providers('cloud', validate, check_existing)


def setup_infrastructure_providers(validate=True, check_existing=True):
    """Run :py:func:`setup_infrastructure_provider` for every infrastructure provider

    Args:
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`


    Returns:
        An list of :py:class:`cfme.infrastructure.provider.Provider` instances.

    """
    return _setup_providers('infra', validate, check_existing)


def setup_container_providers(validate=True, check_existing=True):
    """Run :py:func:`setup_container_provider` for every container provider

    Args:
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`


    Returns:
        An list of :py:class:`cfme.container.provider.Provider` instances.

    """
    return _setup_providers('container', validate, check_existing)


def clear_cloud_providers(validate=True):
    sel.force_navigate('clouds_providers')
    logger.debug('Checking for existing cloud providers...')
    total = paginator.rec_total()
    if total > 0:
        logger.info(' Providers exist, so removing all cloud providers')
        paginator.results_per_page('100')
        sel.click(paginator.check_all())
        toolbar.select('Configuration', 'Remove Cloud Providers from the VMDB',
                       invokes_alert=True)
        sel.handle_alert()
        if validate:
            wait_for_no_cloud_providers()


def clear_infra_providers(validate=True):
    sel.force_navigate('infrastructure_providers')
    logger.debug('Checking for existing infrastructure providers...')
    total = paginator.rec_total()
    if total > 0:
        logger.info(' Providers exist, so removing all infra providers')
        paginator.results_per_page('100')
        sel.click(paginator.check_all())
        toolbar.select('Configuration', 'Remove Infrastructure Providers from the VMDB',
                       invokes_alert=True)
        sel.handle_alert()
        if validate:
            wait_for_no_infra_providers()


def clear_container_providers(validate=True):
    sel.force_navigate('containers_providers')
    logger.debug('Checking for existing container providers...')
    total = paginator.rec_total()
    if total > 0:
        logger.info(' Providers exist, so removing all container providers')
        paginator.results_per_page('100')
        sel.click(paginator.check_all())
        toolbar.select('Configuration', 'Remove Containers Providers from the VMDB',
                       invokes_alert=True)
        sel.handle_alert()
        if validate:
            wait_for_no_container_providers()


def get_paginator_value():
    return paginator.rec_total()


def wait_for_no_cloud_providers():
    sel.force_navigate('clouds_providers')
    logger.debug('Waiting for all cloud providers to disappear...')
    wait_for(lambda: get_paginator_value() == 0, message="Delete all cloud providers",
             num_sec=1000, fail_func=sel.refresh)


def wait_for_no_infra_providers():
    sel.force_navigate('infrastructure_providers')
    logger.debug('Waiting for all infra providers to disappear...')
    wait_for(lambda: get_paginator_value() == 0, message="Delete all infrastructure providers",
             num_sec=1000, fail_func=sel.refresh)


def wait_for_no_container_providers():
    sel.force_navigate('containers_providers')
    logger.debug('Waiting for all container providers to disappear...')
    wait_for(lambda: get_paginator_value() == 0, message="Delete all container providers",
             num_sec=1000, fail_func=sel.refresh)


def clear_providers():
    """Rudely clear all providers on an appliance

    Uses the UI in an attempt to cleanly delete the providers
    """
    # Executes the deletes first, then validates in a second pass
    logger.info('Destroying all appliance providers')
    perflog.start('utils.providers.clear_providers')
    clear_cloud_providers(validate=False)
    clear_infra_providers(validate=False)
    if version.current_version() > '5.5':
        clear_container_providers(validate=False)
    wait_for_no_cloud_providers()
    wait_for_no_infra_providers()
    if version.current_version() > '5.5':
        wait_for_no_container_providers()
    perflog.stop('utils.providers.clear_providers')


def destroy_vm(provider_mgmt, vm_name):
    """Given a provider backend and VM name, destroy an instance with logging and error guards

    Returns ``True`` if the VM is deleted, ``False`` if the backend reports that it did not delete
        the VM, and ``None`` if an error occurred (the error will be logged)

    """
    try:
        if provider_mgmt.does_vm_exist(vm_name):
            logger.info('Destroying VM %s', vm_name)
            vm_deleted = provider_mgmt.delete_vm(vm_name)
            if vm_deleted:
                logger.info('VM %s destroyed', vm_name)
            else:
                logger.error('Destroying VM %s failed for unknown reasons', vm_name)
            return vm_deleted
    except Exception as e:
        logger.error('%s destroying VM %s (%s)', type(e).__name__, vm_name, e.message)


def get_credentials_from_config(credential_config_name, cred_type=None):
    creds = conf.credentials[credential_config_name]
    domain = creds.get('domain', None)
    token = creds.get('token', None)
    return BaseProvider.Credential(
        principal=creds['username'],
        secret=creds['password'],
        cred_type=cred_type,
        domain=domain,
        token=token)


def get_crud(provider_config_name):
    """
    Creates a Provider object given a yaml entry in cfme_data.

    Usage:
        get_crud('ec2east')

    Returns: A Provider object that has methods that operate on CFME
    """

    prov_config = conf.cfme_data.get('management_systems', {})[provider_config_name]
    credentials = get_credentials_from_config(prov_config['credentials'])
    prov_type = prov_config.get('type')

    if prov_type != 'ec2':
        if prov_config.get('discovery_range', None):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')

    if prov_type == 'ec2':
        from cfme.cloud.provider import EC2Provider
        return EC2Provider(name=prov_config['name'],
            region=prov_config['region'],
            credentials={'default': credentials},
            zone=prov_config['server_zone'],
            key=provider_config_name)
    elif prov_type == 'openstack':
        from cfme.cloud.provider import OpenStackProvider
        return OpenStackProvider(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            api_port=prov_config['port'],
            credentials={'default': credentials},
            zone=prov_config['server_zone'],
            key=provider_config_name,
            infra_provider=prov_config.get('infra_provider'))
    elif prov_type == 'virtualcenter':
        return VMwareProvider(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials={'default': credentials},
            zone=prov_config['server_zone'],
            key=provider_config_name,
            start_ip=start_ip,
            end_ip=end_ip)
    elif prov_type == 'scvmm':
        return SCVMMProvider(
            name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials={'default': credentials},
            key=provider_config_name,
            start_ip=start_ip,
            end_ip=end_ip,
            sec_protocol=prov_config['sec_protocol'],
            sec_realm=prov_config['sec_realm'])
    elif prov_type == 'rhevm':
        if prov_config.get('candu_credentials', None):
            candu_credentials = get_credentials_from_config(
                prov_config['candu_credentials'], cred_type='candu')
        else:
            candu_credentials = None
        return RHEVMProvider(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            api_port='',
            credentials={'default': credentials,
                         'candu': candu_credentials},
            zone=prov_config['server_zone'],
            key=provider_config_name,
            start_ip=start_ip,
            end_ip=end_ip)
    elif prov_type == "openstack-infra":
        return OpenstackInfraProvider(
            name=prov_config['name'],
            sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials={'default': credentials},
            key=provider_config_name,
            start_ip=start_ip,
            end_ip=end_ip)
    elif prov_type == 'kubernetes':
        token_creds = get_credentials_from_config(prov_config['credentials'], cred_type='token')
        return KubernetesProvider(
            name=prov_config['name'],
            credentials={'token': token_creds},
            key=provider_config_name,
            zone=prov_config['server_zone'],
            hostname=prov_config.get('hostname', None) or prov_config['ip_address'],
            port=prov_config['port'],
            provider_data=prov_config)
    elif prov_type == 'openshift':
        token_creds = get_credentials_from_config(prov_config['credentials'], cred_type='token')
        return OpenshiftProvider(
            name=prov_config['name'],
            credentials={'token': token_creds},
            key=provider_config_name,
            zone=prov_config['server_zone'],
            hostname=prov_config.get('hostname', None) or prov_config['ip_address'],
            port=prov_config['port'],
            provider_data=prov_config)
    else:
        raise UnknownProviderType('{} is not a known provider type'.format(prov_type))


class UnknownProvider(Exception):
    def __init__(self, provider_key, *args, **kwargs):
        super(UnknownProvider, self).__init__(provider_key, *args, **kwargs)
        self.provider_key = provider_key

    def __str__(self):
        return ('Unknown provider: "%s"' % self.provider_key)
