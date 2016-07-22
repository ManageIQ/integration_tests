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
from cfme.containers import provider as container_providers  # NOQA
from cfme.cloud import provider as cloud_providers  # NOQA
from cfme.infrastructure import provider as infrastructure_providers  # NOQA
from cfme.middleware import provider as middleware_providers  # NOQA
from fixtures.prov_filter import filtered
from utils import conf, version
from utils.log import logger, perflog
from utils.wait import wait_for


providers_data = conf.cfme_data.get("management_systems", {})

# This is a global variable. Not the most ideal way to do things but how can we track bad providers?
problematic_providers = set([])


def list_providers(allowed_types=None):
    """ Returns list of providers of selected type from configuration.

    @param allowed_types: Passed by partial(), see top of this file.
    @type allowed_types: dict, list, set, tuple
    """
    if not allowed_types:
        allowed_types = [
            k2 for k in BaseProvider.type_mapping.keys() for k2 in BaseProvider.type_mapping[k]
        ]
    providers = []
    for provider, data in providers_data.items():
        provider_type = data.get("type", None)
        if provider not in filtered:
            continue
        assert provider_type is not None, "Provider {} has no type specified!".format(provider)
        if provider_type in allowed_types:
            providers.append(provider)
    return providers


def get_mgmt(provider_key, providers=None, credentials=None):
    """
    Provides a ``mgmtsystem`` object, based on the request.

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
    if isinstance(provider_key, Mapping):
        provider = provider_key
    else:
        provider = providers[provider_key]

    if credentials is None:
        # We need to handle the in-place credentials
        credentials = provider['credentials']
        # If it is not a mapping, it most likely points to a credentials yaml (as by default)
        if not isinstance(credentials, Mapping):
            credentials = conf.credentials[credentials]
        # Otherwise it is a mapping and therefore we consider it credentials

    # Munge together provider dict and creds,
    # Let the provider do whatever they need with them
    provider_kwargs = provider.copy()
    provider_kwargs.update(credentials)
    if isinstance(provider_key, basestring):
        provider_kwargs['provider_key'] = provider_key
    provider_kwargs['logger'] = logger

    return _get_provider_class_by_type(provider['type']).mgmt_class(**provider_kwargs)


def _get_provider_class_by_type(prov_type):
    for _, class_dict in BaseProvider.type_mapping.iteritems():
        for ptype, the_class in class_dict.iteritems():
            if ptype == prov_type:
                return the_class


def get_provider_key(provider_name):
    for provider_key, provider_data in providers_data.items():
        if provider_data.get("name") == provider_name:
            return provider_key
    else:
        raise NameError("Could not find provider {}".format(provider_name))


def get_mgmt_by_name(provider_name, *args, **kwargs):
    """Provides a ``mgmtsystem`` object, based on the request.

    For detailed parameter description, refer to the :py:func:`get_mgmt` (except its
    `provider_key` parameter)

    Args:
        provider_name: 'Nice' provider name (name field from provider's YAML entry)
    Return: A provider instance of the appropriate ``mgmtsystem``
        subclass
    """
    return get_mgmt(get_provider_key(provider_name), *args, **kwargs)


def setup_a_provider(prov_class="infra", prov_type=None, validate=True, check_existing=True,
                     required_keys=None):
    """Sets up a single provider robustly.

    Does some counter-badness measures.

    Args:
        prov_class: "infra", "cloud", "container" or "middleware"
        prov_type: "ec2", "virtualcenter" or any other valid type
        validate: Whether to validate the provider.
        check_existing: Whether to check if the provider already exists.
        required_keys: A set of required keys for the provider data to have
    """
    if not required_keys:
        required_keys = []
    potential_providers = list_providers(BaseProvider.type_mapping[prov_class].keys())
    if prov_type:
        providers = []
        for provider in potential_providers:
            if providers_data[provider]['type'] == prov_type:
                providers.append(provider)
    else:
        providers = potential_providers

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


def existing_providers():
    """Lists all providers that are already set up in the appliance."""
    return filter(is_provider_setup, list_providers())


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
        logger.info('Setting up provider: %s', provider.key)
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
    for pclass in prov_classes:
        added_providers.extend(_setup_providers(pclass, **setup_kwargs))

    if validate:
        map(methodcaller('validate'), added_providers)

    perflog.stop('utils.providers.setup_providers')

    return added_providers


def _setup_providers(prov_class, validate, check_existing):
    """Helper to set up all cloud, infra or container providers, and then validate them

    Args:
        prov_class: Provider class - 'cloud, 'infra', 'container' or 'middleware' (a string)
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    Returns:
        A list of provider objects that have been created.

    """

    # Check for existing providers all at once, to prevent reloading
    # the providers page for every provider in cfme_data
    if not list_providers(BaseProvider.type_mapping[prov_class]):
        return []
    if check_existing:
        navigate = "{}_providers".format(
            BaseProvider.type_mapping[prov_class].values()[0].page_name)
        sel.force_navigate(navigate)
        add_providers = []
        for provider_key in list_providers(BaseProvider.type_mapping[prov_class].keys()):
            provider_name = conf.cfme_data.get('management_systems', {})[provider_key]['name']
            quad_name = BaseProvider.type_mapping[prov_class].values()[0].quad_name
            quad = Quadicon(provider_name, quad_name)
            for page in paginator.pages():
                if sel.is_displayed(quad):
                    logger.debug('Provider %s exists, skipping', provider_key)
                    break
            else:
                add_providers.append(provider_key)
    else:
        # Add all cloud, infra or container providers unconditionally
        add_providers = list_providers(BaseProvider.type_mapping[prov_class].keys())

    if add_providers:
        logger.info('Providers to be added: %s', ', '.join(add_providers))

    # Save the provider objects for validation and return
    added_providers = []

    for provider_name in add_providers:
        # Don't validate in this step; add all providers, then go back and validate in order
        provider = setup_provider(provider_name, validate=False, check_existing=False)
        added_providers.append(provider)

    if validate:
        map(methodcaller('validate'), added_providers)

    return added_providers


def wait_for_no_providers_by_type(prov_class):
    navigate = "{}_providers".format(BaseProvider.type_mapping[prov_class].values()[0].page_name)
    sel.force_navigate(navigate)
    logger.debug('Waiting for all {} providers to disappear...'.format(prov_class))
    wait_for(
        lambda: get_paginator_value() == 0, message="Delete all {} providers".format(prov_class),
        num_sec=1000, fail_func=sel.refresh
    )


def clear_provider_by_type(prov_class, validate=True):
    string_name = BaseProvider.type_mapping[prov_class].values()[0].string_name
    navigate = "{}_providers".format(BaseProvider.type_mapping[prov_class].values()[0].page_name)
    sel.force_navigate(navigate)
    logger.debug('Checking for existing {} providers...'.format(prov_class))
    total = paginator.rec_total()
    if total > 0:
        logger.info(' Providers exist, so removing all {} providers'.format(prov_class))
        paginator.results_per_page('100')
        sel.click(paginator.check_all())
        toolbar.select('Configuration', 'Remove {} Providers from the VMDB'.format(string_name),
                       invokes_alert=True)
        sel.handle_alert()
        if validate:
            wait_for_no_providers_by_type(prov_class)


def get_paginator_value():
    return paginator.rec_total()


def clear_providers():
    """Rudely clear all providers on an appliance

    Uses the UI in an attempt to cleanly delete the providers
    """
    # Executes the deletes first, then validates in a second pass
    logger.info('Destroying all appliance providers')
    perflog.start('utils.providers.clear_providers')
    clear_provider_by_type('cloud', validate=False)
    clear_provider_by_type('infra', validate=False)
    if version.current_version() > '5.5':
        clear_provider_by_type('container', validate=False)
    if version.current_version() == version.LATEST:
        clear_provider_by_type('middleware', validate=False)
    wait_for_no_providers_by_type('cloud')
    wait_for_no_providers_by_type('infra')
    if version.current_version() > '5.5':
        wait_for_no_providers_by_type('container')
    if version.current_version() == version.LATEST:
        wait_for_no_providers_by_type('middleware')
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
        logger.error('%s destroying VM %s (%s)', type(e).__name__, vm_name, str(e))


def get_crud(provider_config_name):
    """
    Creates a Provider object given a yaml entry in cfme_data.

    Usage:
        get_crud('ec2east')

    Returns: A Provider object that has methods that operate on CFME
    """

    prov_config = conf.cfme_data.get('management_systems', {})[provider_config_name]
    prov_type = prov_config.get('type')

    return _get_provider_class_by_type(prov_type).configloader(prov_config, provider_config_name)
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
    if prov_type == 'gce':
        from cfme.cloud.provider import GCEProvider
        ser_acc_creds = get_credentials_from_config(
            prov_config['credentials'], cred_type='service_account')
        return GCEProvider(name=prov_config['name'],
            project=prov_config['project'],
            zone=prov_config['zone'],
            region=prov_config['region'],
            credentials={'default': ser_acc_creds},
            key=provider_config_name)
    elif prov_type == 'azure':
        from cfme.cloud.provider import AzureProvider
        return AzureProvider(name=prov_config['name'],
            provisioning=prov_config['provisioning'],
            tenant_id=prov_config['tenant_id'],
            subscription_id=prov_config['subscription_id'],
            credentials={'default': credentials},
            key=provider_config_name)
    elif prov_type == 'openstack':
        from cfme.cloud.provider import OpenStackProvider
        credentials_dict = {'default': credentials}
        if 'amqp_credentials' in prov_config:
            credentials_dict['amqp'] = process_credential_yaml_key(
                prov_config['amqp_credentials'], cred_type='amqp')
        return OpenStackProvider(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            api_port=prov_config['port'],
            credentials=credentials_dict,
            zone=prov_config['server_zone'],
            key=provider_config_name,
            sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
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
        credential_dict = {'default': credentials}
        if prov_config.get('candu_credentials', None):
            credential_dict['candu'] = process_credential_yaml_key(
                prov_config['candu_credentials'], cred_type='candu')
        return RHEVMProvider(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            api_port='',
            credentials=credential_dict,
            zone=prov_config['server_zone'],
            key=provider_config_name,
            start_ip=start_ip,
            end_ip=end_ip)
    elif prov_type == "openstack-infra":
        credential_dict = {'default': credentials}
        if 'ssh_credentials' in prov_config:
            credential_dict['ssh'] = process_credential_yaml_key(
                prov_config['ssh_credentials'], cred_type='ssh')
        if 'amqp_credentials' in prov_config:
            credential_dict['amqp'] = process_credential_yaml_key(
                prov_config['amqp_credentials'], cred_type='amqp')
        return OpenstackInfraProvider(
            name=prov_config['name'],
            sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials=credential_dict,
            key=provider_config_name,
            start_ip=start_ip,
            end_ip=end_ip)
    elif prov_type == 'kubernetes':
        token_creds = process_credential_yaml_key(prov_config['credentials'], cred_type='token')
        return KubernetesProvider(
            name=prov_config['name'],
            credentials={'token': token_creds},
            key=provider_config_name,
            zone=prov_config['server_zone'],
            hostname=prov_config.get('hostname', None) or prov_config['ip_address'],
            port=prov_config['port'],
            provider_data=prov_config)
    elif prov_type == 'openshift':
        token_creds = process_credential_yaml_key(prov_config['credentials'], cred_type='token')
        return OpenshiftProvider(
            name=prov_config['name'],
            credentials={'token': token_creds},
            key=provider_config_name,
            zone=prov_config['server_zone'],
            hostname=prov_config.get('hostname', None) or prov_config['ip_address'],
            port=prov_config['port'],
            provider_data=prov_config)
    elif prov_type == 'hawkular':
        return HawkularProvider(
            name=prov_config['name'],
            key=provider_config_name,
            hostname=prov_config['hostname'],
            port=prov_config['port'],
            credentials={'default': credentials})
    else:
        raise UnknownProviderType('{} is not a known provider type'.format(prov_type))

class UnknownProvider(Exception):
    def __init__(self, provider_key, *args, **kwargs):
        super(UnknownProvider, self).__init__(provider_key, *args, **kwargs)
        self.provider_key = provider_key

    def __str__(self):
        return ('Unknown provider: "{}"'.format(self.provider_key))
