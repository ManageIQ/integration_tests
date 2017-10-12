import attr

from navmazing import NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import SecurityGroupDetailsView, SecurityGroupView
from cfme.utils import version
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


@attr.s
class SecurityGroup(WidgetasticTaggable, BaseEntity):
    """Class representing security group in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'security_group'
    string_name = 'SecurityGroup'
    quad_name = None
    db_types = ['SecurityGroup']

    name = attr.ib()

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)

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
class SecurityGroupCollection(BaseCollection):
    """ Collection object for SecurityGroup object
        Note: Network providers object are not implemented in mgmt
    """
    ENTITY = SecurityGroup

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'SecurityGroups')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=s.name) for s in list_networks_obj]


@navigator.register(SecurityGroupCollection, 'All')
class All(CFMENavigateStep):
    VIEW = SecurityGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Security Groups')


@navigator.register(SecurityGroup, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = SecurityGroupDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()
