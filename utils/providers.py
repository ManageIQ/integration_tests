"""
utils.provider
--------------

Provides a simple function to return a provider instance of :py:mod:`utils.mgmt_system`
based on the request

:var infra_provider_type_map: Provides mapping of infra provider type names a
   :py:mod:`utils.mgmt_system` object as a dict
:var cloud_provider_type_map: Provides mapping of cloud provider type names a
   :py:mod:`utils.mgmt_system` object as a dict
:var provider_type_map: Combined dict of ``infra_provider_type_map`` and ``cloud_provider_type_map``
"""
from utils import conf, mgmt_system
from functools import partial

# infra and cloud provider type maps, useful for type checking
infra_provider_type_map = {
    'virtualcenter': mgmt_system.VMWareSystem,
    'rhevm': mgmt_system.RHEVMSystem,
}

cloud_provider_type_map = {
    'ec2': mgmt_system.EC2System,
    'openstack': mgmt_system.OpenstackSystem,
}

# Combined type map, provider_factory doesn't discriminate
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
    Return: A provider instance of :py:mod:`utils.mgmt_system`
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


list_infra_providers = partial(list_providers, infra_provider_type_map.keys())
list_cloud_providers = partial(list_providers, cloud_provider_type_map.keys())
list_all_providers = partial(list_providers, provider_type_map.keys())
