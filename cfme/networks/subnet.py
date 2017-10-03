import attr

from navmazing import NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import SubnetDetailsView, SubnetView
from cfme.utils import providers, version
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


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

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'CloudSubnets')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all()
        return [self.instantiate(name=p.name) for p in list_networks_obj]


@navigator.register(SubnetCollection, 'All')
class All(CFMENavigateStep):
    VIEW = SubnetView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Subnets')


@navigator.register(Subnet, 'Details')
class OpenCloudNetworks(CFMENavigateStep):
    VIEW = SubnetDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()
