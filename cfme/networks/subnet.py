import attr

from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.networks.views import (SubnetDetailsView, SubnetView, SubnetAddView,
                                 SubnetEditView)
from cfme.utils import providers, version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


@attr.s
class Subnet(WidgetasticTaggable, BaseEntity):
    """Class representing subnets in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'network_subnet'
    string_name = 'NetworkSubnet'
    quad_name = None
    db_types = ['NetworkSubnet']

    name = attr.ib()

    def edit(self, new_name, gateway=None):
        """Edit cloud subnet

        Args:
            new_name: (str) new name of subnet
            gateway: (str) IP of new gateway, for example: 11.11.11.1
        """
        view = navigate_to(self, 'Edit')
        view.fill({'subnet_name': new_name,
                   'gateway': gateway})
        view.save.click()
        view.flash.assert_success_message('Network Subnet "{}" updated'.format(new_name))
        self.name = new_name

    def delete(self):
        """Deletes this subnet"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Delete this Cloud Subnet', handle_alert=True)
        view.flash.assert_success_message('The selected Cloud Subnet was deleted')

    @property
    def cloud_tenant(self):
        """ Return name of tenant that subnet belongs to"""
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud tenant')

    @property
    def cloud_network(self):
        """ Return name of network that subnet belongs to"""
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud network')

    @property
    def cidr(self):
        """ Return subnet's CIDR"""
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Cidr')

    @property
    def net_protocol(self):
        """ Return subnet's network protocol"""
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Network protocol')

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

    @property
    def zone(self):
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Zone')


@attr.s
class SubnetCollection(BaseCollection):
    """ Collection object for Subnet object
        Note: Network providers object are not implemented in mgmt
    """

    ENTITY = Subnet

    def create(self, name, tenant, provider, network_manager, network_name,
               cidr, dhcp=True, gateway=None):
        """Create subnet

        Args:
            name: (str) name of the subnet
            tenant: (str) name of the tenant to place subnet to
            provider: crud object of Openstack cloud provider
            network_manager: (str) name of network manager
            network_name: (str) name of the network to create subnet under
            cidr: (str) ip version and CIDR of subnet, for example: ("4", "192.168.12.2/24")
            gateway: (str) gateway of subnet, if None - appliance will set it automatically

        Returns: instance of cfme.newtorks.subnet.Subnet
        """
        view = navigate_to(self, 'Add')
        view.fill({'network_manager': network_manager,
                   'subnet_name': name,
                   'enable_dhcp': dhcp,
                   'subnet_cidr': cidr[1],
                   'gateway': gateway})
        if current_version() < '5.9':
            view.network_protocol.select_by_visible_text(cidr[0])
            view.network.select_by_visible_text(network_name)
        else:
            view.network_protocol_new.select_by_visible_text("ipv{}".format(cidr[0]))
            view.network_new.select_by_visible_text(network_name)
        view.cloud_tenant.select_by_visible_text(tenant)
        view.add.click()
        view.flash.assert_success_message('Cloud Subnet "{}" created'.format(name))
        subnet = self.instantiate(name)
        # Refresh provider's relationships to have new subnet displayed
        provider.refresh_provider_relationships()
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        return subnet

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'CloudSubnets')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all()
        return [self.instantiate(name=p.name) for p in list_networks_obj]

    def exists(self, subnet):
        routers = [r.name for r in self.all()]
        return subnet.name in routers


@navigator.register(SubnetCollection, 'All')
class All(CFMENavigateStep):
    VIEW = SubnetView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Subnets')


@navigator.register(Subnet, 'Details')
class OpenCloudNetworks(CFMENavigateStep):
    VIEW = SubnetDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name).click()


@navigator.register(SubnetCollection, 'Add')
class AddSubnet(CFMENavigateStep):
    VIEW = SubnetAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Cloud Subnet')


@navigator.register(Subnet, 'Edit')
class EditSubnet(CFMENavigateStep):
    VIEW = SubnetEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Cloud Subnet')
