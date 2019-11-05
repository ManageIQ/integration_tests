from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BootstrapSwitch
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import TextInput

from cfme.common import BaseLoggedInPage
from cfme.common.provider_views import ProviderAddView
from cfme.common.provider_views import ProviderEditView
from cfme.exceptions import displayed_not_implemented
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import ParametrizedSummaryTable
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Table


class NetworkProviderToolBar(View):
    """ Represents provider toolbar and its controls """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class NetworkProviderDetailsToolBar(NetworkProviderToolBar):
    """ Represents provider details toolbar """
    monitoring = Dropdown(text='Monitoring')
    download = Button(title='Print or export summary')


class NetworkProviderSideBar(View):
    """ Represents left side bar, usually contains navigation, filters, etc """
    pass


class NetworkProviderDetailsSideBar(View):
    """ Represents left side bar of network providers details """
    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class NetworkProviderEntities(BaseEntitiesView):
    """ Represents central view where all QuadIcons, etc are displayed """
    pass


class NetworkProviderAddView(ProviderAddView):
    """
     represents Network Provider Add View
    """
    prov_type = BootstrapSelect(id='ems_type')
    api_version = BootstrapSelect(id='api_version')

    @property
    def is_displayed(self):
        return (super(NetworkProviderAddView, self).is_displayed and
                self.navigation.currently_selected == [
                    'Networks', 'Providers'] and
                self.title.text == 'Add New Network Provider')


class NetworkProviderView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    toolbar = View.nested(NetworkProviderToolBar)
    sidebar = View.nested(NetworkProviderSideBar)
    search = View.nested(Search)

    including_entities = View.include(NetworkProviderEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == 'Network Managers')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class NetworkProviderDetailsView(BaseLoggedInPage):
    """ Represents detail view of network provider """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(NetworkProviderDetailsToolBar)
    sidebar = View.nested(NetworkProviderDetailsSideBar)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        # TODO: remove all SummaryTables in favor of ParametrizedSummaryTable when safe
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        status = SummaryTable(title="Status")
        overview = SummaryTable(title="Overview")
        smart_management = SummaryTable(title="Smart Management")

        summary = ParametrizedSummaryTable

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.title.text == self.context['object'].expected_details_title)


class NetworkProviderEditView(ProviderEditView):
    """ Represents Network Provider Edit View """
    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.title.text.startswith('Edit Network Provider'))


class BalancerToolBar(View):
    """ Represents balancers toolbar and its controls """
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class BalancerDetailsToolBar(BalancerToolBar):
    """ Represents details toolbar of balancer summary """
    download = Button(title='Print or export summary')


class BalancerSideBar(View):
    """ Represents left side bar, usually contains navigation, filters, etc """
    pass


class BalancerDetailsSideBar(View):
    """ Represents left side bar of balancer details """
    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class BalancerEntities(BaseEntitiesView):
    """ Represents central view where all QuadIcons, etc are displayed """
    pass


class BalancerView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    toolbar = View.nested(BalancerToolBar)
    sidebar = View.nested(BalancerSideBar)
    search = View.nested(Search)
    including_entities = View.include(NetworkProviderEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Load Balancers'] and
                self.entities.title.text == 'Load Balancers')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class BalancerDetailsView(BaseLoggedInPage):
    """ Represents detail view of network provider """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(BalancerDetailsToolBar)
    sidebar = View.nested(BalancerDetailsSideBar)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Load Balancers'] and
                self.title.text == self.context['object'].expected_details_title)


class CloudNetworkToolBar(View):
    """ Represents cloud networks toolbar and its controls """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class CloudNetworkDetailsToolBar(View):
    """ Represents provider details toolbar """
    policy = Dropdown(text='Policy')
    download = Button(title='Print or export summary')


class CloudNetworkSideBar(View):
    """ Represents left side bar, usually contains navigation, filters, etc """
    pass


class CloudNetworkDetailsSideBar(View):
    """ Represents left side bar of network providers details """
    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class CloudNetworkEntities(BaseEntitiesView):
    """ Represents central view where all QuadIcons, etc are displayed """
    pass


class CloudNetworkView(BaseLoggedInPage):
    """ Represents whole All Cloud network page """
    toolbar = View.nested(CloudNetworkToolBar)
    sidebar = View.nested(CloudNetworkSideBar)
    search = View.nested(Search)
    including_entities = View.include(NetworkProviderEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Networks'] and
                self.entities.title.text == 'Cloud Networks')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class CloudNetworkDetailsView(BaseLoggedInPage):
    """ Represents detail view of cloud network """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(NetworkProviderDetailsToolBar)
    sidebar = View.nested(NetworkProviderDetailsSideBar)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Networks'] and
                self.title.text == self.context['object'].expected_details_title)


class CloudNetworkAddView(BaseLoggedInPage):
    """ Represents Add view of cloud network """
    title = Text('//div[@id="main-content"]//h1')
    network_manager = Select(id='ems_id')
    cloud_tenant = Select(name='cloud_tenant_id')
    network_type = Select(name='provider_network_type')
    network_name = TextInput(name='name')
    ext_router = BootstrapSwitch(id='cloud_network_external_facing')
    administrative_state = BootstrapSwitch(id='cloud_network_enabled')
    shared = BootstrapSwitch(id='cloud_network_shared')
    add = Button('Add')

    is_displayed = displayed_not_implemented


class CloudNetworkEditView(BaseLoggedInPage):
    """ Represents Edit view of cloud network """
    title = Text('//div[@id="main-content"]//h1')
    network_name = TextInput(name='name')
    ext_router = BootstrapSwitch(id='cloud_network_external_facing')
    administrative_state = BootstrapSwitch(id='cloud_network_enabled')
    shared = BootstrapSwitch(id='cloud_network_shared')
    save = Button('Save')

    is_displayed = displayed_not_implemented


class NetworkPortToolBar(View):
    """ Represents provider toolbar and its controls """
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class NetworkPortDetailsToolBar(View):
    """ Represents toolbar of summary of port """
    policy = Dropdown(text='Policy')
    download = Button(title='Print or export summary')


class NetworkPortSideBar(View):
    """ Represents left side bar, usually contains navigation, filters, etc """
    pass


class NetworkPortDetailsSideBar(View):
    """ Represents left side bar of network providers details """
    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class NetworkPortEntities(BaseEntitiesView):
    """ Represents central view where all QuadIcons, etc are displayed """
    pass


class NetworkPortView(BaseLoggedInPage):
    """ Represents whole All NetworkPorts page """
    toolbar = View.nested(NetworkPortToolBar)
    sidebar = View.nested(NetworkPortSideBar)
    search = View.nested(Search)
    including_entities = View.include(NetworkPortEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Networks', 'Network Ports'] and
                self.entities.title.text == 'Network Ports')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class SubnetNetworkPortView(NetworkPortView):
    """ Represents a Subnet network with port view"""
    title = Text('//div[@id="main-content"]//h1')

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Subnets'] and
                self.title.text == '{name} (All Network Ports)'.format(
                    name=self.context['object'].name))


class NetworkPortDetailsView(BaseLoggedInPage):
    """ Represents detail view of network provider """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(NetworkPortDetailsToolBar)
    sidebar = View.nested(NetworkPortDetailsSideBar)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Network Ports'] and
                self.title.text == self.context['object'].expected_details_title)


class NetworkRouterToolBar(View):
    """ Represents provider toolbar and its controls """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class NetworkRouterDetailsToolBar(View):
    """ Represents provider toolbar and its controls """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    edit = Dropdown(text='Edit')
    download = Button(title='Print or export summary')


class NetworkRouterSideBar(View):
    """ Represents left side bar, usually contains navigation, filters, etc """
    pass


class NetworkRouterDetailsSideBar(View):
    """ Represents left side bar of network providers details """
    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class NetworkRouterEntities(BaseEntitiesView):
    """ Represents central view where all QuadIcons, etc are displayed """
    pass


class NetworkRouterView(BaseLoggedInPage):
    """ Represents whole All NetworkRouters page """
    toolbar = View.nested(NetworkRouterToolBar)
    sidebar = View.nested(NetworkRouterSideBar)
    search = View.nested(Search)
    including_entities = View.include(NetworkRouterEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Network Routers'] and
                self.entities.title.text == 'Network Routers')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class NetworkRouterDetailsView(BaseLoggedInPage):
    """ Represents detail view of network provider """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(NetworkRouterDetailsToolBar)
    sidebar = View.nested(NetworkRouterDetailsSideBar)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Network Routers'] and
                self.title.text == self.context['object'].expected_details_title)


class NetworkRouterAddView(BaseLoggedInPage):
    """ Represents Add NetworkRouters page """
    network_manager = Select(id='ems_id')
    router_name = TextInput(name='name')
    ext_gateway = BootstrapSwitch(name='external_gateway')
    network_name = Select(name='cloud_network_id')
    subnet_name = Select(name='cloud_subnet_id')
    cloud_tenant = Select(name='cloud_tenant_id')
    add = Button('Add')

    is_displayed = displayed_not_implemented


class NetworkRouterEditView(BaseLoggedInPage):
    """ Represents Edit NetworkRouters page """
    router_name = TextInput(name='name')
    ext_gateway = BootstrapSwitch(name='external_gateway')
    network_name = Select(name='cloud_network_id')
    subnet_name = Select(name='cloud_subnet_id')
    save = Button('Save')

    is_displayed = displayed_not_implemented


class NetworkRouterAddInterfaceView(BaseLoggedInPage):
    """ Represents Add Interface to Network Router page """
    subnet_name = Select(id='cloud_subnet_id')
    add = Button('Add')

    is_displayed = displayed_not_implemented


class NetworkRouterAddCloudSubnetView(BaseLoggedInPage):
    """ Represents Add Interface to Network Router page """
    modal_title = Text('//div[@class="modal-header"]//h4')
    subnet_name = TextInput(id='name')
    address = TextInput(id='address')
    netmask = TextInput(id='netmask')
    gateway = TextInput(id='gateway')
    add = Button('Add')


class SecurityGroupToolBar(View):
    """ Represents provider toolbar and its controls """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class SecurityGroupDetailsToolBar(View):
    """ Represents provider details toolbar """
    policy = Dropdown(text='Policy')
    download = Button(title='Print or export summary')
    view_selector = View.nested(ItemsToolBarViewSelector)


class SecurityGroupSideBar(View):
    """ Represents left side bar, usually contains navigation, filters, etc """
    pass


class SecurityGroupDetailsSideBar(View):
    """ Represents left side bar of network providers details """
    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class SecurityGroupEntities(BaseEntitiesView):
    """ Represents central view where all QuadIcons, etc are displayed """
    pass


class SecurityGroupView(BaseLoggedInPage):
    """ Represents whole All SecurityGroups page """
    toolbar = View.nested(SecurityGroupToolBar)
    sidebar = View.nested(SecurityGroupSideBar)
    search = View.nested(Search)
    including_entities = View.include(SecurityGroupEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Security Groups'] and
                self.entities.title.text == 'Security Groups')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class ProviderSecurityGroupAllView(SecurityGroupView):

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
            self.entities.title.text == '{} (All Security Groups)'.format(
                self.context['object'].name)
        )


class SecurityGroupDetailsView(BaseLoggedInPage):
    """ Represents detail view of network provider """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(SecurityGroupDetailsToolBar)
    sidebar = View.nested(SecurityGroupDetailsSideBar)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")
        firewall_rules = Table(
            locator='//th[normalize-space(.) = "Firewall Rules"]/ancestor::table[1]')

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Security Groups'] and
                self.title.text == self.context['object'].expected_details_title)


class SubnetToolBar(View):
    """ Represents provider toolbar and its controls """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class SubnetDetailsToolBar(View):
    """ Represents provider details toolbar """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    download = Button(title='Print or export summary')


class SubnetAddView(BaseLoggedInPage):
    """ Represents Add view of subnet """
    title = Text('//div[@id="main-content"]//h1')
    network_manager = Select(name='ems_id')
    cloud_tenant = Select(name='cloud_tenant_id')
    network = Select(name='network_id')
    subnet_name = TextInput(name='name')
    subnet_cidr = TextInput(name='cidr')
    gateway = TextInput(name='gateway_ip')
    add = Button('Add')

    is_displayed = displayed_not_implemented


class SubnetEditView(BaseLoggedInPage):
    """ Represents Edit view of subnet """
    title = Text('//div[@id="main-content"]//h1')
    subnet_name = TextInput(name='name')
    gateway = TextInput(name='gateway_ip')
    save = Button('Save')

    is_displayed = displayed_not_implemented


class SubnetSideBar(View):
    """ Represents left side bar, usually contains navigation, filters, etc """
    pass


class SubnetDetailsSideBar(View):
    """ Represents left side bar of network providers details """
    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class SubnetEntities(BaseEntitiesView):
    """ Represents central view where all QuadIcons, etc are displayed """
    pass


class SubnetView(BaseLoggedInPage):
    """ Represents whole All Subnets page """
    toolbar = View.nested(SubnetToolBar)
    sidebar = View.nested(SubnetSideBar)
    search = View.nested(Search)
    including_entities = View.include(SubnetEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Subnets'] and
                self.entities.title.text == 'Cloud Subnets')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class SubnetDetailsView(BaseLoggedInPage):
    """ Represents detail view of network provider """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(SubnetDetailsToolBar)
    sidebar = View.nested(SubnetDetailsSideBar)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Subnets'] and
                self.title.text == self.context['object'].expected_details_title)


class NetworkEntitySubnetView(BaseLoggedInPage):
    """
    Represents a view for use with a network entity that
    includes SubnetCollection in its _collections
    """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(SubnetToolBar)
    sidebar = View.nested(SubnetSideBar)
    including_entities = View.include(SubnetEntities, use_parent=True)

    @property
    def is_displayed(self):
        obj = self.context['object']
        matched_title = ('{name} (All Cloud Subnets)'.format(
            name=self.context['object'].name) == self.entities.title.text
        )
        if obj.string_name == 'Tenant':
            matched_navigation = self.navigation.currently_selected == ['Compute', 'Clouds',
                                                                        'Tenants']
        elif obj.string_name == 'NetworkRouter':
            matched_navigation = self.navigation.currently_selected == ['Networks',
                                                                        'Network Routers']
        else:
            matched_navigation = False
        return super(BaseLoggedInPage, self).is_displayed and matched_navigation and matched_title


class OneProviderComponentsToolbar(View):
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    back = Button(name='show_summary')
    view_selector = View.nested(ItemsToolBarViewSelector)


class OneProviderSubnetView(BaseLoggedInPage):
    """ Represents whole All Subnets page """
    toolbar = View.nested(OneProviderComponentsToolbar)
    sidebar = View.nested(SubnetSideBar)
    including_entities = View.include(SubnetEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = '{name} (All Cloud Subnets)'.format(name=self.context['object'].name)
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == title)


class OneProviderBalancerView(BaseLoggedInPage):
    """ Represents whole All Subnets page """
    toolbar = View.nested(OneProviderComponentsToolbar)
    sidebar = View.nested(BalancerSideBar)
    including_entities = View.include(BalancerEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = '{name} (All Load Balancers)'.format(name=self.context['object'].name)
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == title)


class OneProviderNetworkPortView(BaseLoggedInPage):
    """ Represents whole All Subnets page """
    toolbar = View.nested(OneProviderComponentsToolbar)
    sidebar = View.nested(NetworkPortSideBar)
    including_entities = View.include(NetworkPortEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = '{name} (All Network Ports)'.format(name=self.context['object'].name)
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == title)


class OneProviderCloudNetworkView(BaseLoggedInPage):
    """ Represents whole All Subnets page """
    toolbar = View.nested(OneProviderComponentsToolbar)
    sidebar = View.nested(CloudNetworkSideBar)
    including_entities = View.include(CloudNetworkEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = '{name} (All Cloud Networks)'.format(name=self.context['object'].name)
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == title)


class OneProviderNetworkRouterView(BaseLoggedInPage):
    """ Represents whole All Subnets page """
    toolbar = View.nested(OneProviderComponentsToolbar)
    sidebar = View.nested(NetworkRouterSideBar)
    including_entities = View.include(NetworkRouterEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = '{name} (All Network Routers)'.format(name=self.context['object'].name)
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == title)


class OneTenantNetworkRouterView(BaseLoggedInPage):
    """ Represents whole All Subnets page """
    toolbar = View.nested(NetworkRouterToolBar)
    sidebar = View.nested(NetworkRouterSideBar)
    including_entities = View.include(NetworkRouterEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = '{name} (All Network Routers)'.format(name=self.context['object'].name)
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Tenants'] and
                self.entities.title.text == title)


class OneProviderSecurityGroupView(BaseLoggedInPage):
    """ Represents whole All Subnets page """
    toolbar = View.nested(OneProviderComponentsToolbar)
    sidebar = View.nested(SecurityGroupSideBar)
    including_entities = View.include(SecurityGroupEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = '{name} (All Security Groups)'.format(name=self.context['object'].name)
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == title)


class FloatingIpToolBar(View):
    """ Represents floating ips toolbar and its controls """
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class FloatingIpDetailsToolBar(View):
    """ Represents toolbar of summary of port """
    policy = Dropdown(text='Policy')
    download = Button(title='Print or export summary')


class FloatingIpDetailsSideBar(View):
    """ Represents left side bar of floating ip details """
    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = ManageIQTree()


class FloatingIpEntities(BaseEntitiesView):
    """ Represents central view where all QuadIcons, etc are displayed """
    pass


class FloatingIpView(BaseLoggedInPage):
    """ Represents whole All FloatingIP page """
    toolbar = View.nested(FloatingIpToolBar)
    search = View.nested(Search)
    including_entities = View.include(FloatingIpEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (self.navigation.currently_selected == ['Networks', 'Floating IPs'] and
                self.entities.title.text == 'Floating IPs')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class FloatingIpDetailsView(BaseLoggedInPage):
    """ Represents detail view of floating ip """
    toolbar = View.nested(FloatingIpDetailsToolBar)
    sidebar = View.nested(FloatingIpDetailsSideBar)
    search = View.nested(Search)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        title = Text('//div[@id="main-content"]//h1')
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (self.navigation.currently_selected == ['Networks', 'Floating IPs'] and
                self.entities.title.text == '{} (Summary)'.format(self.context['object'].address))


class OneProviderFloatingIpView(BaseLoggedInPage):
    """ Represents Floating Ip all for specific Network provider """

    toolbar = View.nested(OneProviderComponentsToolbar)
    including_entities = View.include(FloatingIpEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = "{name} (All Floating IPs)".format(name=self.context["object"].name)
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected == ["Networks", "Providers"]
            and self.entities.title.text == title
        )


class OneHostSubnetView(SubnetView):
    @property
    def is_displayed(self):
        expected_title = '{name} (All Cloud Subnets)'.format(name=self.context['object'].name)
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Nodes'] and
                self.entities.title.text == expected_title
                )
