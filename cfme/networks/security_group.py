import attr
from navmazing import NavigateToAttribute

from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.modeling.base import parent_of_type
from cfme.networks.views import SecurityGroupDetailsView
from cfme.networks.views import SecurityGroupView
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator


@attr.s
class SecurityGroup(Taggable, BaseEntity, CustomButtonEventsMixin):
    """Class representing security group in sdn"""
    category = 'networks'
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
            net_prov_collection = self.appliance.collections.network_provider
            return net_prov_collection.instantiate(name=prov_name)
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

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Networks', 'Security Groups')

    def resetter(self, *args, **kwargs):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(SecurityGroup, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = SecurityGroupDetailsView

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
