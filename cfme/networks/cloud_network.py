import attr

from navmazing import NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import CloudNetworkAddView, CloudNetworkDetailsView, CloudNetworkView
from cfme.utils import providers, version
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


@attr.s
class CloudNetwork(WidgetasticTaggable, BaseEntity):
    """Class representing cloud networks in cfme database"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'cloud_network'
    string_name = 'CloudNetwork'
    quad_name = None
    db_types = ['CloudNetwork']

    name = attr.ib()

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)

    @property
    def parent_provider(self):
        """ Return object of parent cloud provider """
        view = navigate_to(self, 'Details')
        provider_name = view.entities.relationships.get_text_of('Parent ems cloud')
        return providers.get_crud_by_name(provider_name)

    @property
    def network_type(self):
        """ Return type of network """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Type')

    @property
    def network_provider(self):
        """ Returns network provider """
        # security group collection contains reference to provider
        if self.provider:
            return self.provider
        # otherwise get provider name from ui
        view = navigate_to(self, 'Details')
        try:
            prov_name = view.entities.relationships.get_text_of("Network Manager")
            collection = self.appliance.collections.network_provider
            return collection.instantiate(name=prov_name)
        except ItemNotFound:  # BZ 1480577
            return None


@attr.s
class CloudNetworkCollection(BaseCollection):
    """Collection object for Cloud Network object"""
    ENTITY = CloudNetwork

    def create(self, name, tenant, provider, network_manager, network_type, is_external=False,
               admin_state='up', is_shared=False):
        view = navigate_to(self, 'Add')
        view.network_manager.fill(network_manager)
        view.cloud_tenant.fill(tenant)
        view.network_type.fill(network_type)
        view.network_name.fill(name)
        if is_external:
            view.ext_router.click()
        if admin_state.lower() == 'down':
            view.administrative_state.click()
        if is_shared:
            view.shared.click()
        view.save.click()
        view.flash.assert_success_message('Cloud Network "{}" created'.format(self.name))
        return self.instantiate(name, provider)

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'CloudNetworks')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=n.name) for n in list_networks_obj]


@navigator.register(CloudNetworkCollection, 'All')
class All(CFMENavigateStep):
    VIEW = CloudNetworkView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Networks')


@navigator.register(CloudNetwork, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = CloudNetworkDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()


@navigator.register(CloudNetworkCollection, 'Add')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = CloudNetworkAddView

    def step(self):
        self.prerequisite_view.configuration.item_select('Add a new Cloud Network')
