"""Function to return a provider instance of :py:mod:`utils.mgmt_system`
based on the request

:var infra_provider_type_map: Provides mapping of infra provider type names a
   :py:mod:`utils.mgmt_system` object as a dict
:var cloud_provider_type_map: Provides mapping of cloud provider type names a
   :py:mod:`utils.mgmt_system` object as a dict
:var provider_type_map: Combined dict of ``infra_provider_type_map`` and ``cloud_provider_type_map``
"""
from functools import partial

from fixtures import navigation
from utils import conf, mgmt_system
from utils.browser import browser
from utils.wait import wait_for

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


def setup_provider(provider_name):
    provider_data = conf.cfme_data['management_systems'][provider_name]
    if provider_data['type'] in infra_provider_type_map:
        setup_infrastructure_provider(provider_name, provider_data)
    elif provider_data['type'] in cloud_provider_type_map:
        setup_cloud_provider(provider_name, provider_data)
    #else: wat?


def setup_infrastructure_provider(provider_name, provider_data):
    infra_providers_pg = navigation.infra_providers_pg()

    # Bail out if the provider already exists
    if infra_providers_pg.quadicon_region.does_quadicon_exist(provider_data['name']):
        return

    add_pg = infra_providers_pg.click_on_add_new_provider()
    add_pg.fill_provider(provider_data)
    if not add_pg.validate():
        # Bad credentials? Don't go any farther...
        failmsg = 'Invalid credentials for provider "%s", testing cannot continue' % provider_name
        raise Exception(failmsg)

    add_pg.click_on_add()
    expected_flash_message = 'Infrastructure Providers "%s" was saved' % provider_data['name']
    if infra_providers_pg.flash.message != expected_flash_message:
        # Doesn't exit to allow for debugging.
        failmsg = 'Provider "%s" was not saved for unknown reasons.' % provider_name
        raise Exception(failmsg)

    # wait for the quadicon to show up
    infra_providers_pg.taskbar_region.view_buttons.change_to_grid_view()

    def provider_quadicon_exists():
        browser().refresh()
        return infra_providers_pg.quadicon_region.does_quadicon_exist(provider_data['name'])
    wait_for(provider_quadicon_exists)

    # Poke the provider until the numbers are right
    provider_data['request'] = provider_name
    infra_providers_pg.wait_for_provider_or_timeout(provider_data)


def setup_cloud_provider(provider_name, provider_data):
    raise NotImplementedError('sooooooooon...')


list_infra_providers = partial(list_providers, infra_provider_type_map.keys())
list_cloud_providers = partial(list_providers, cloud_provider_type_map.keys())
list_all_providers = partial(list_providers, provider_type_map.keys())
