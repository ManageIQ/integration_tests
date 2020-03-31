import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import Version
from widgetastic.utils import VersionPick

from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.modeling.base import parent_of_type
from cfme.networks.views import CloudNetworkAddView
from cfme.networks.views import CloudNetworkDetailsView
from cfme.networks.views import CloudNetworkEditView
from cfme.networks.views import CloudNetworkView
from cfme.utils import providers
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.wait import wait_for


@attr.s
class CloudNetwork(Taggable, BaseEntity, CustomButtonEventsMixin):
    """Class representing cloud networks in cfme database"""
    category = 'networks'
    string_name = 'CloudNetwork'
    quad_name = None
    db_types = ['CloudNetwork']

    name = attr.ib()
    provider_obj = attr.ib(default=None)

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)

    @property
    def parent_provider(self):
        """ Return object of parent cloud provider """
        view = navigate_to(self, 'Details')
        parent_cloud_text = VersionPick({Version.lowest(): 'Parent ems cloud',
                                         '5.10': 'Parent Cloud Provider'}
                                        ).pick(self.appliance.version)
        provider_name = view.entities.relationships.get_text_of(parent_cloud_text)
        return providers.get_crud_by_name(provider_name)

    @property
    def network_type(self):
        """ Return type of network """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Type')

    @property
    def cloud_tenant(self):
        """Return name of tenant that network belongs to"""
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud tenant')

    def edit(self, name, change_external=None, change_admin_state=None, change_shared=None):
        """Edit cloud network

        Args:
            name: (str) new network name
            change_external: (bool) is network external
            change_admin_state: (bool) network's administrative state, 'Up' or 'Down'
            change_shared: (bool) is network shared, 'Yes' or 'No'
        """
        view = navigate_to(self, 'Edit')
        view.fill({'network_name': name,
                   'ext_router': change_external,
                   'administrative_state': change_admin_state,
                   'shared': change_shared})
        view.save.click()
        view.flash.assert_success_message(f'Cloud Network "{name}" updated')
        self.name = name

    def delete(self):
        """Delete this cloud network"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Delete this Cloud Network', handle_alert=True)
        view.flash.assert_success_message('Delete initiated for 1 Cloud Network.')

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
               admin_state=True, is_shared=False):
        """Create cloud network

        Args:
            name: (str) name of the network
            tenant: (str) name of cloud tenant to place network to
            provider: crud object of Openstack Cloud provider
            network_manager: (str) name of network manager
            network_type: (str) type of network, such as 'VXLAN', 'VLAN', 'GRE' etc.
            is_external: (bool) is network external
            admin_state: (bool) network's initial administrative state, True stands for 'Up',
                            False - 'Down'
            is_shared: (bool) is network shared
        Returns:
            instance of cfme.networks.cloud_network.CloudNetwork
        """
        view = navigate_to(self, 'Add')
        view.fill({'network_manager': network_manager,
                   'cloud_tenant': tenant,
                   'network_type': network_type,
                   'network_name': name,
                   'ext_router': is_external,
                   'administrative_state': admin_state,
                   'shared': is_shared})
        view.add.click()
        view.flash.assert_success_message(f'Cloud Network "{name}" created')
        network = self.instantiate(name, provider)
        # Refresh provider's relationships to have new network displayed
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        wait_for(lambda: network.exists, timeout=100, fail_func=network.browser.refresh)
        return network

    def all(self):
        """returning all Cloud Network objects and support filtering as per provider"""
        provider_id = self.filters.get("provider").id if self.filters.get("provider") else None
        networks_all = self.appliance.rest_api.collections.cloud_networks.all
        prov_db = {prov.id: prov for prov in self.appliance.rest_api.collections.providers}

        nw_objs = []
        for nw in networks_all:
            prov_name = prov_db[prov_db[nw.ems_id].parent_ems_id]["name"]
            prov = providers.get_crud_by_name(prov_name)
            nw_objs.append(self.instantiate(name=nw.name, provider_obj=prov))

        if provider_id:
            return [nw for nw in nw_objs if nw.provider_obj.id == provider_id]
        else:
            return nw_objs


@navigator.register(CloudNetworkCollection, 'All')
class All(CFMENavigateStep):
    VIEW = CloudNetworkView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Networks', 'Networks')

    def resetter(self, *args, **kwargs):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(CloudNetwork, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = CloudNetworkDetailsView

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(CloudNetworkCollection, 'Add')
class Add(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = CloudNetworkAddView

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Cloud Network')


@navigator.register(CloudNetwork, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = CloudNetworkEditView

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Cloud Network')
