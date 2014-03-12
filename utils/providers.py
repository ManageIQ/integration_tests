"""Helper functions related to the creation and destruction of providers

To quickly add all providers::

    setup_providers(validate=False)

"""
from functools import partial
from operator import methodcaller

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Quadicon, paginator, toolbar
from utils import conf, mgmt_system
from utils.log import logger, perflog
from utils.wait import wait_for

#: mapping of infra provider type names to :py:mod:`utils.mgmt_system` classes
infra_provider_type_map = {
    'virtualcenter': mgmt_system.VMWareSystem,
    'rhevm': mgmt_system.RHEVMSystem,
}

#: mapping of cloud provider type names to :py:mod:`utils.mgmt_system` classes
cloud_provider_type_map = {
    'ec2': mgmt_system.EC2System,
    'openstack': mgmt_system.OpenstackSystem,
}

#: mapping of all provider type names to :py:mod:`utils.mgmt_system` classes
provider_type_map = dict(
    infra_provider_type_map.items() + cloud_provider_type_map.items()
)


def list_providers(allowed_types):
    """ Returns list of providers of selected type from configuration.

    @param allowed_types: Passed by partial(), see top of this file.
    @type allowed_types: dict, list, set, tuple
    """
    providers = []
    for provider, data in conf.cfme_data["management_systems"].iteritems():
        provider_type = data.get("type", None)
        assert provider_type is not None, "Provider %s has no type specified!" % provider
        if provider_type in allowed_types:
            providers.append(provider)
    return providers

#: function that returns a list of infra provider keys in cfme_data
list_infra_providers = partial(list_providers, infra_provider_type_map.keys())

#: function that returns a list of cloud provider keys in cfme_data
list_cloud_providers = partial(list_providers, cloud_provider_type_map.keys())

#: function that returns a list of all provider keys in cfme_data
list_all_providers = partial(list_providers, provider_type_map.keys())


def provider_factory(provider_name, providers=None, credentials=None):
    """
    Provides a :py:mod:`utils.mgmt_system` object, based on the request.

    Args:
        provider_name: The name of a provider, as supplied in the yaml configuration files
        providers: A set of data in the same format as the ``management_systems`` section in the
            configuration yamls. If ``None`` then the configuration is loaded from the default
            locations. Expects a dict.
        credentials: A set of credentials in the same format as the ``credentials`` yamls files.
            If ``None`` then credentials are loaded from the default locations. Expects a dict.
    Return: A provider instance of the appropriate :py:class:`utils.mgmt_system.MgmtSystemAPIBase`
        subclass
    """
    if providers is None:
        providers = conf.cfme_data['management_systems']

    provider = providers[provider_name]

    if credentials is None:
        credentials = conf.credentials[provider['credentials']]

    # Munge together provider dict and creds,
    # Let the provider do whatever they need with them
    provider_kwargs = provider.copy()
    provider_kwargs.update(credentials)
    provider_instance = provider_type_map[provider['type']](**provider_kwargs)
    return provider_instance


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
        `cfme.infrastructure.provider.Provider`for the named provider, as appropriate.

    """
    if provider_key in list_cloud_providers():
        from cfme.cloud.provider import get_from_config
        #provider = setup_infrastructure_provider(provider_key, validate, check_existing)
    elif provider_key in list_infra_providers():
        from cfme.infrastructure.provider import get_from_config
    else:
        raise UnknownProvider(provider_key)

    provider = get_from_config(provider_key)
    if check_existing and provider.exists:
        return

    logger.info('Setting up provider: %s' % provider.key)
    provider.create(validate_credentials=True)

    if validate:
        provider.validate()

    return provider


def setup_providers(validate=True, check_existing=True):
    """Run :py:func:`setup_provider` for every provider (cloud and infra)

    Args:
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
    added_providers.extend(setup_cloud_providers(**setup_kwargs))
    added_providers.extend(setup_infrastructure_providers(**setup_kwargs))

    if validate:
        map(methodcaller('validate'), added_providers)

    perflog.stop('utils.providers.setup_providers')

    return added_providers


def _setup_providers(cloud_or_infra, validate, check_existing):
    """Helper to set up all cloud or infra providers, and then validate them

    Args:
        cloud_or_infra: Like the name says: 'cloud' or 'infra' (a string)
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    Returns:
        A list of provider objects that have been created.

    """
    # Pivot behavior on cloud_or_infra
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
        }
    }
    # Check for existing providers all at once, to prevent reloading
    # the providers page for every provider in cfme_data
    if check_existing:
        sel.force_navigate(options_map[cloud_or_infra]['navigate'])
        add_providers = []
        for provider_key in options_map[cloud_or_infra]['list']():
            provider_name = conf.cfme_data['management_systems'][provider_key]['name']
            quad = Quadicon(provider_name, options_map[cloud_or_infra]['quad'])
            for page in paginator.pages():
                if sel.is_displayed(quad):
                    logger.debug('Provider "%s" exists, skipping' % provider_key)
                    break
            else:
                add_providers.append(provider_key)
    else:
        # Add all cloud or infra providers unconditionally
        add_providers = options_map[cloud_or_infra]['list']()

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


def clear_cloud_providers(validate=True):
    sel.force_navigate('clouds_providers')
    logger.debug('Checking for existing cloud providers...')
    if paginator.rec_total():
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
    if paginator.rec_total():
        logger.info(' Providers exist, so removing all infra providers')
        paginator.results_per_page('100')
        sel.click(paginator.check_all())
        toolbar.select('Configuration', 'Remove Infrastructure Providers from the VMDB',
                       invokes_alert=True)
        sel.handle_alert()
        if validate:
            wait_for_no_infra_providers()


def wait_for_no_cloud_providers():
    sel.force_navigate('clouds_providers')
    logger.debug('Waiting for all cloud providers to disappear...')
    wait_for(lambda: not paginator.rec_total(), message="Delete all cloud providers",
             num_sec=700, fail_func=sel.refresh)


def wait_for_no_infra_providers():
    sel.force_navigate('infrastructure_providers')
    logger.debug('Waiting for all infra providers to disappear...')
    wait_for(lambda: not paginator.rec_total(), message="Delete all infrastructure providers",
             num_sec=700, fail_func=sel.refresh)


def clear_providers():
    """Rudely clear all providers on an appliance

    Uses the UI in an attempt to cleanly delete the providers
    """
    # Executes the deletes first, then validates in a second pass
    logger.info('Destroying all appliance providers')
    perflog.start('utils.providers.clear_providers')
    clear_cloud_providers(validate=False)
    clear_infra_providers(validate=False)
    wait_for_no_cloud_providers()
    wait_for_no_cloud_providers()
    perflog.stop('utils.providers.clear_providers')


class UnknownProvider(Exception):
    def __init__(self, provider_key, *args, **kwargs):
        super(UnknownProvider, self).__init__(provider_key, *args, **kwargs)
        self.provider_key = provider_key

    def __str__(self):
        return ('Unknown provider: "%s"' % self.provider_key)
