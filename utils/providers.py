"""Function to return a provider instance of :py:mod:`utils.mgmt_system`
based on the request

:var infra_provider_type_map: Provides mapping of infra provider type names a
   :py:mod:`utils.mgmt_system` object as a dict
:var cloud_provider_type_map: Provides mapping of cloud provider type names a
   :py:mod:`utils.mgmt_system` object as a dict
:var provider_type_map: Combined dict of ``infra_provider_type_map`` and ``cloud_provider_type_map``
"""
from functools import partial

from utils import conf, mgmt_system

#: infra provider type maps, useful for type checking
infra_provider_type_map = {
    'virtualcenter': mgmt_system.VMWareSystem,
    'rhevm': mgmt_system.RHEVMSystem,
}

#: cloud provider type maps, useful for type checking
cloud_provider_type_map = {
    'ec2': mgmt_system.EC2System,
    'openstack': mgmt_system.OpenstackSystem,
}

#: Combined type map, used by :py:func:`provider_factory` to create provider instances
provider_type_map = dict(
    infra_provider_type_map.items() + cloud_provider_type_map.items()
)


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


def setup_provider(provider_name, validate=True):
    """Add the named provider to CFME

    Args:
        provider_name: Provider name from cfme_data
        validate: Whether or not to block until the provider stats in CFME
            match the stats gleaned from the backend management system
            (default: ``True``)

    """
    provider_data = conf.cfme_data['management_systems'][provider_name]
    if provider_data['type'] in infra_provider_type_map:
        setup_infrastructure_provider(provider_name, validate)
    elif provider_data['type'] in cloud_provider_type_map:
        setup_cloud_provider(provider_name, validate)
    #else: wat?


def setup_cloud_provider(provider_name, validate=True):
    """Add the named cloud provider to CFME

    Args:
        provider_name: Provider name from cfme_data
        validate: see description in :py:func:`setup_provider`

    """
    from cfme.cloud.provider import get_from_config
    provider = get_from_config(provider_name)
    provider.create(validate_credentials=True)
    if validate:
        provider.validate()


def setup_infrastructure_provider(provider_name, validate=True):
    """Add the named infrastructure provider to CFME

    Args:
        provider_name: Provider name from cfme_data
        validate: see description in :py:func:`setup_provider`

    """
    from cfme.infrastructure.provider import get_from_config
    provider = get_from_config(provider_name)
    provider.create(validate_credentials=True)
    if validate:
        provider.validate()


def setup_providers(validate=True):
    """Run :py:func:`setup_provider` for every provider (cloud and infra)

    Args:
        validate: see description in :py:func:`setup_provider`

    """
    for provider_name in list_all_providers():
        setup_provider(provider_name, validate)


def setup_cloud_providers(validate=True):
    """Run :py:func:`setup_cloud_provider` for every cloud provider

    Args:
        validate: see description in :py:func:`setup_provider`

    """
    for provider_name in list_cloud_providers():
        setup_cloud_provider(provider_name, validate)


def setup_infrastructure_providers(validate=True):
    """Run :py:func:`setup_infrastructure_provider` for every infrastructure provider

    Args:
        validate: see description in :py:func:`setup_provider`

    """
    for provider_name in list_infra_providers():
        setup_infrastructure_provider(provider_name, validate)


list_infra_providers = partial(list_providers, infra_provider_type_map.keys())
list_cloud_providers = partial(list_providers, cloud_provider_type_map.keys())
list_all_providers = partial(list_providers, provider_type_map.keys())
