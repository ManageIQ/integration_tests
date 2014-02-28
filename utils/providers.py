"""Helper functions related to the creation and destruction of providers

To quickly add all providers::

    setup_providers(validate=False)

"""
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Quadicon, paginator, toolbar
from utils import conf, mgmt_system
from utils.log import logger
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


def setup_provider(provider_name, validate=True, check_existing=True):
    """Add the named provider to CFME

    Args:
        provider_name: Provider name from cfme_data
        validate: Whether or not to block until the provider stats in CFME
            match the stats gleaned from the backend management system
            (default: ``True``)
        check_existing: Check if this provider already exists, skip if it does

    """
    provider_data = conf.cfme_data['management_systems'][provider_name]
    if provider_data['type'] in infra_provider_type_map:
        setup_infrastructure_provider(provider_name, validate, check_existing)
    elif provider_data['type'] in cloud_provider_type_map:
        setup_cloud_provider(provider_name, validate, check_existing)
    #else: wat?


def setup_cloud_provider(provider_name, validate=True, check_existing=True):
    """Add the named cloud provider to CFME

    Args:
        provider_name: Provider name from cfme_data
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    """
    from cfme.cloud.provider import get_from_config
    provider = get_from_config(provider_name)
    if check_existing and provider.exists:
        return

    logger.info('Setting up provider: %s' % provider.key)
    provider.create(validate_credentials=True)
    if validate:
        provider.validate()


def setup_infrastructure_provider(provider_name, validate=True, check_existing=True):
    """Add the named infrastructure provider to CFME

    Args:
        provider_name: Provider name from cfme_data
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    """
    from cfme.infrastructure.provider import get_from_config
    provider = get_from_config(provider_name)
    if check_existing and provider.exists:
        return

    logger.info('Setting up provider: %s' % provider.key)
    provider.create(validate_credentials=True)
    if validate:
        provider.validate()


def setup_providers(validate=True, check_existing=True):
    """Run :py:func:`setup_provider` for every provider (cloud and infra)

    Args:
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    """
    setup_cloud_providers(validate, check_existing)
    setup_infrastructure_providers(validate, check_existing)


def setup_cloud_providers(validate=True, check_existing=True):
    """Run :py:func:`setup_cloud_provider` for every cloud provider

    Args:
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    """
    # Check for existing providers all at once, to prevent reloading
    # the providers page for every provider in cfme_data
    if check_existing:
        providers_to_add = []
        sel.force_navigate('clouds_providers')
        for provider_key in list_cloud_providers():
            provider_name = conf.cfme_data['management_systems'][provider_key]['name']
            quad = Quadicon(provider_name, 'cloud_prov')
            for page in paginator.pages():
                if sel.is_displayed(quad):
                    logger.debug('Provider "%s" exists, skipping' % provider_key)
                    break
            else:
                providers_to_add.append(provider_key)
    else:
        providers_to_add = list_cloud_providers()

    if providers_to_add:
        logger.info('Providers to be added: %s' % ', '.join(providers_to_add))

    for provider_name in providers_to_add:
        setup_cloud_provider(provider_name, validate, check_existing=False)


def setup_infrastructure_providers(validate=True, check_existing=True):
    """Run :py:func:`setup_infrastructure_provider` for every infrastructure provider

    Args:
        validate: see description in :py:func:`setup_provider`
        check_existing: see description in :py:func:`setup_provider`

    """
    if check_existing:
        providers_to_add = []
        sel.force_navigate('infrastructure_providers')
        for provider_key in list_infra_providers():
            provider_name = conf.cfme_data['management_systems'][provider_key]['name']
            quad = Quadicon(provider_name, 'infra_prov')
            for page in paginator.pages():
                if sel.is_displayed(quad):
                    logger.debug('Provider "%s" exists, skipping' % provider_key)
                    break
            else:
                providers_to_add.append(provider_key)
    else:
        providers_to_add = list_infra_providers()

    if providers_to_add:
        logger.info('Providers to be added: %s' % ', '.join(providers_to_add))

    for provider_name in providers_to_add:
        setup_infrastructure_provider(provider_name, validate, check_existing=False)


def clear_providers():
    """Rudely clear all providers on an appliance

    Uses the UI in an attempt to cleanly delete the providers
    """
    logger.info('Destroying all appliance providers')
    sel.force_navigate('clouds_providers')
    if paginator.rec_total():
        paginator.results_per_page('100')
        sel.click(paginator.check_all())
        toolbar.select('Configuration', 'Remove Cloud Providers from the VMDB',
                       invokes_alert=True)
        sel.handle_alert()

    sel.force_navigate('infrastructure_providers')
    if paginator.rec_total():
        paginator.results_per_page('100')
        sel.click(paginator.check_all())
        toolbar.select('Configuration', 'Remove Infrastructure Providers from the VMDB',
                       invokes_alert=True)
        sel.handle_alert()

    sel.force_navigate('clouds_providers')
    wait_for(lambda: not paginator.rec_total(), message="Delete all cloud providers",
             num_sec=180, fail_func=sel.refresh)

    sel.force_navigate('infrastructure_providers')
    wait_for(lambda: not paginator.rec_total(), message="Delete all infrastructure providers",
             num_sec=180, fail_func=sel.refresh)
