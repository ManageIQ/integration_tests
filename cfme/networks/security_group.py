from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.networks.views import SecurityGroupDetailsView, SecurityGroupView
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class SecurityGroupCollection(Navigatable):
    """ Collection object for SecurityGroup object
        Note: Network providers object are not implemented in mgmt
    """
    def __init__(self, appliance=None, parent_provider=None):
        self.appliance = appliance
        self.parent = parent_provider

    def instantiate(self, name):
        return SecurityGroup(name=name, appliance=self.appliance)

    def all(self):
        view = navigate_to(SecurityGroup, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=s.name) for s in list_networks_obj]


class SecurityGroup(WidgetasticTaggable, Navigatable):
    """Class representing security group in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'security_group'
    string_name = 'SecurityGroup'
    quad_name = None
    db_types = ['SecurityGroup']

    def __init__(self, name, provider=None, collection=None, appliance=None):
        self.collection = collection or SecurityGroupCollection(appliance=appliance)
        Navigatable.__init__(self, appliance=self.collection.appliance)
        self.name = name
        self.provider = provider


@navigator.register(SecurityGroup, 'All')
class All(CFMENavigateStep):
    VIEW = SecurityGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Security Groups')


@navigator.register(SecurityGroup, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = SecurityGroupDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()


@navigator.register(SecurityGroup, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.tb = self.view.toolbar
        self.tb.policy.item_select('Edit Tags')
