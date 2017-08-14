from utils import version
from cfme.common.provider import BaseProvider
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from widgetastic_manageiq import (ManageIQTree, SummaryTable, ItemsToolBarViewSelector,
                                  BaseEntitiesView)
from widgetastic_patternfly import Dropdown, Accordion, FlashMessages
from widgetastic.widget import View, Text
from utils.wait import wait_for
from cfme.base.login import BaseLoggedInPage


class NetworkProviderToolBar(View):
    ''' Represents provider toolbar and its controls '''
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class NetworkProviderDetailsToolBar(NetworkProviderToolBar):
    ''' Represents provider details toolbar '''
    monitoring = Dropdown(text='Monitoring')


class NetworkProviderSideBar(View):
    ''' Represents left side bar, usually contains navigation, filters, etc '''
    pass


class NetworkProviderDetailsSideBar(View):
    ''' Represents left side bar of network providers details '''
    @View.nested
    class properties(Accordion):
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class NetworkProviderEntities(BaseEntitiesView):
    ''' Represents central view where all QuadIcons, etc are displayed '''
    pass


class NetworkProviderView(BaseLoggedInPage):
    ''' Represents whole All NetworkProviders page '''
    flash = FlashMessages('.//div[@div="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    toolbar = View.nested(NetworkProviderToolBar)
    sidebar = View.nested(NetworkProviderSideBar)
    including_entities = View.include(NetworkProviderEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == 'Network Managers')


class NetworkProviderDetailsView(BaseLoggedInPage):
    ''' Represents detail view of network provider '''
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    toolbar = View.nested(NetworkProviderDetailsToolBar)
    sidebar = View.nested(NetworkProviderDetailsSideBar)

    @View.nested
    class contents(View):
        ''' Represents details page when it's switched to Summary/Table view '''
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        status = SummaryTable(title="Status")
        overview = SummaryTable(title="Overview")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.title.text == '{name} (Summary)'.format(name=self.context['object'].name))


class NetworkProviderCollection(Navigatable):
    ''' Collection object for NetworkProvider object
        Note: Network providers object are not implemented in mgmt
    '''

    def instantiate(self, name, provider):
        return NetworkProvider(name=name, appliance=self.appliance)

    def all(self):
        navigate_to(NetworkProvider, 'All')
        list_networks_obj = []
        list_network = [q.name for q in Quadicon.all()]
        for network in list_network:
            list_networks_obj.append(NetworkProvider(name=network))
        return list_networks_obj


class NetworkProvider(BaseProvider):
    ''' Class representing network provider in sdn
        Note: Network provider can be added to cfme database
              only automaticaly with cloud provider
    '''
    STATS_TO_MATCH = []
    string_name = 'Networks'
    in_version = ('5.8', version.LATEST)
    page_name = 'networks'
    edit_page_suffix = ""
    detail_page_suffix = ""
    refresh_text = "Refresh items and relationships"
    quad_name = None
    category = "networks"
    provider_types = {}
    property_tuples = []
    detail_page_suffix = 'provider_detail'
    db_types = ["NetworksManager"]

    def __init__(
            self, name=None, key=None, zone=None, provider_data=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.key = key
        self.provider_data = provider_data
        self.zone = zone

    def refresh_provider(self, cancel=True):
        ''' Refresh relationships of network provider '''
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Refresh Relationships and Power States',
                                               handle_alert=not cancel)

    def delete(self, cancel=True):
        ''' Deltes a network provider from CFME '''
        view = navigate_to(self, 'Details')
        wait_for(lambda: view.toolbar.configuration.item_enabled('Remove this Network Provider'),
                 fail_condition=False, num_sec=10)
        view.toolbar.configuration.item_select('Remove this Network Provider',
                                               handle_alert=not cancel)

    def check_default_credentials_state(self):
        ''' Checks whether credentials are valid '''
        view = navigate_to(self, 'Details')
        cred_state = view.contents.status.get_text_of('Default Credentials')
        if cred_state == "Valid":
            return True
        return False

    @property
    def exists(self):
        view = navigate_to(self, 'Details')
        return view.is_displayed


@navigator.register(NetworkProvider, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkProviderView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Providers')

    def resetter(self):
        # Reset view and selection
        tb = self.view.toolbar
        if tb.view_selector.is_displayed and 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select("Grid View")
        paginator = self.view.entities.paginator
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(NetworkProvider, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = NetworkProviderDetailsView

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()


@navigator.register(NetworkProvider, 'CloudSubnets')
class OpenCloudSubnets(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Cloud Subnets')


@navigator.register(NetworkProvider, 'CloudNetworks')
class OpenCloudNetworks(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Cloud Networks')


@navigator.register(NetworkProvider, 'NetworkRouters')
class OpenNetworkRouters(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Cloud Routers')


@navigator.register(NetworkProvider, 'SecurityGroups')
class OpenSecurityGroups(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Security Groups')


@navigator.register(NetworkProvider, 'FloatingIPs')
class OpenFloatingIPs(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Floating IPs')


@navigator.register(NetworkProvider, 'NetworkPorts')
class OpenNetworkPorts(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Network Ports')


@navigator.register(NetworkProvider, 'LoadBalancers')
class OpenNetworkBalancers(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.relationships.click_at('Load Balancers')


@navigator.register(NetworkProvider, 'TopologyFromDetails')
class OpenTopologyFromDetails(CFMENavigateStep):
    VIEW = NetworkProviderDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.contents.overview.click_at('Topology')
