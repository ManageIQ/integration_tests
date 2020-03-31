import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling

from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.exceptions import DestinationNotFound
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.modeling.base import parent_of_type
from cfme.networks import ValidateStatsMixin
from cfme.networks.network_port import NetworkPortCollection
from cfme.networks.views import SubnetAddView
from cfme.networks.views import SubnetDetailsView
from cfme.networks.views import SubnetEditView
from cfme.networks.views import SubnetNetworkPortView
from cfme.networks.views import SubnetView
from cfme.utils import providers
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.wait import wait_for


@attr.s
class Subnet(Taggable, BaseEntity, CustomButtonEventsMixin, ValidateStatsMixin):
    """Class representing subnets in sdn"""
    category = 'networks'
    string_name = 'NetworkSubnet'
    quad_name = None
    db_types = ['NetworkSubnet']

    name = attr.ib()
    provider_obj = attr.ib(default=None)
    network = attr.ib(default=None)

    _collections = {
        'network_ports': NetworkPortCollection,
    }

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
        view.flash.assert_success_message(f'Cloud Subnet "{new_name}" updated')
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
        return view.entities.relationships.get_text_of('Cloud Network')

    @property
    def cidr(self):
        """ Return subnet's CIDR"""
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('CIDR')

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
        return providers.get_crud_by_name(
            view.entities.relationships.get_text_of('Parent Cloud Provider')
        )

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

    def create(self, name, tenant, provider, network_manager, network_name, cidr, gateway=None):
        """Create subnet

        Args:
            name: (str) name of the subnet
            tenant: (str) name of the tenant to place subnet to
            provider: crud object of Openstack cloud provider
            network_manager: (str) name of network manager
            network_name: (str) name of the network to create subnet under
            cidr: (str) CIDR of subnet, for example: 192.168.12.2/24
            gateway: (str) gateway of subnet, if None - appliance will set it automatically

        Returns: instance of cfme.newtorks.subnet.Subnet
        """
        view = navigate_to(self, 'Add')
        view.fill({'network_manager': network_manager,
                   'network': network_name,
                   'subnet_name': name,
                   'subnet_cidr': cidr,
                   'gateway': gateway,
                   'cloud_tenant': tenant})
        view.add.click()
        view.flash.assert_success_message(f'Cloud Subnet "{name}" created')
        subnet = self.instantiate(name, provider, network_name)
        # Refresh provider's relationships to have new subnet displayed
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        wait_for(lambda: subnet.exists, timeout=100, fail_func=subnet.browser.refresh)
        return subnet

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'CloudSubnets')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=p.name) for p in list_networks_obj]


@navigator.register(SubnetCollection, 'All')
class All(CFMENavigateStep):
    VIEW = SubnetView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Networks', 'Subnets')

    def resetter(self, *args, **kwargs):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(Subnet, 'Details')
class OpenCloudNetworks(CFMENavigateStep):
    VIEW = SubnetDetailsView

    def prerequisite(self, *args, **kwargs):
        """Navigate through filter parent if it exists else navigate through parent object"""
        is_filtered = isinstance(self.obj.parent, BaseCollection) and self.obj.parent.filters
        filter = (self.obj.parent.filters.get('parent') if is_filtered else None)
        if is_filtered:
            return navigate_to(filter, 'CloudSubnets')
        else:
            return navigate_to(self.obj.parent, 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(SubnetCollection, 'Add')
class AddSubnet(CFMENavigateStep):
    VIEW = SubnetAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Cloud Subnet')


@navigator.register(Subnet, 'Edit')
class EditSubnet(CFMENavigateStep):
    VIEW = SubnetEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Cloud Subnet')


@navigator.register(Subnet, 'NetworkPorts')
class NetworkPorts(CFMENavigateStep):
    VIEW = SubnetNetworkPortView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        item = 'Network Ports'
        if not int(self.prerequisite_view.entities.relationships.get_text_of(item)):
            raise DestinationNotFound(
                f'Cloud Subnet {self.obj} has a 0 count for {item} relationships')

        self.prerequisite_view.entities.relationships.click_at(item)
