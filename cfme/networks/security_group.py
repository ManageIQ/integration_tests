from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.update import Updateable
from cfme.common import Taggable, SummaryMixin
from cfme.networks.views import SecurityGroupView
from cfme.networks.views import SecurityGroupDetailsView


class SecurityGroupCollection(Navigatable):
    ''' Collection object for SecurityGroup object
        Note: Network providers object are not implemented in mgmt
    '''

    def instantiate(self, name):
        return SecurityGroup(name=name)

    def all(self):
        view = navigate_to(SecurityGroup, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [SecurityGroup(name=s.name) for s in list_networks_obj]


class SecurityGroup(Taggable, Updateable, SummaryMixin, Navigatable):
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'security_group'
    string_name = 'SecurityGroup'
    quad_name = None
    db_types = ["SecurityGroup"]

    def __init__(
            self, name, provider=None):
        if provider:
            self.appliance = provider.appliance
        else:
            self.appliance = None
        Navigatable.__init__(self, appliance=self.appliance)
        self.name = name
        self.provider = provider


@navigator.register(SecurityGroup, 'All')
class All(CFMENavigateStep):
    VIEW = SecurityGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Security Groups')

    def resetter(self):
        # Reset view and selection
        tb = self.view.toolbar
        if tb.view_selector.is_displayed and 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select("Grid View")
        paginator = self.view.entities.paginator
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(SecurityGroup, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = SecurityGroupDetailsView

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()


@navigator.register(SecurityGroup, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = SecurityGroupDetailsView

    def step(self):
        self.tb = self.view.toolbar
        self.tb.policy.item_select('Edit Tags')
