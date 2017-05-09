# -*- coding: utf-8 -*-
from widgetastic_manageiq import (BreadCrumb,
                                  SummaryTable,
                                  Button,
                                  TimelinesView,
                                  DetailsToolBarViewSelector,
                                  ItemsToolBarViewSelector,
                                  Checkbox,
                                  Input,
                                  Table,
                                  PaginationPane,
                                  FileInput,
                                  Search,
                                  DynaTree,
                                  BootstrapTreeview)
from widgetastic_patternfly import Dropdown, BootstrapSelect
from widgetastic.widget import View, Text
from widgetastic.utils import VersionPick, Version

from cfme.base.login import BaseLoggedInPage


class ProviderDetailsToolBar(View):
    """
    represents provider toolbar and its controls
    """
    monitoring = Dropdown(text='Monitoring')
    configuration = Dropdown(text='Configuration')
    reload = Button(title='Reload Current Display')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')

    view_selector = View.nested(DetailsToolBarViewSelector)


class ProviderDetailsSummaryView(View):
    """
    represents Details page when it is switched to Summary aka Tables view
    """
    properties = SummaryTable(title="Properties")
    status = SummaryTable(title="Status")
    relationships = SummaryTable(title="Relationships")
    overview = SummaryTable(title="Overview")
    smart_management = SummaryTable(title="Smart Management")


class ProviderDetailsDashboardView(View):
    """
     represents Details page when it is switched to Dashboard aka Widgets view
    """
    # todo: need to develop this page
    pass


class ProviderDetailsView(BaseLoggedInPage):
    """
     main Details page
    """
    title = Text('//div[@id="main-content"]//h1')
    breadcrumb = BreadCrumb(locator='//ol[@class="breadcrumb"]')
    toolbar = View.nested(ProviderDetailsToolBar)

    @View.nested
    class contents(View):  # NOQA
        # this is switchable view that gets replaced with concrete view.
        # it gets changed according to currently chosen view type  every time
        # when it is accessed
        # it is provided provided by __getattribute__
        pass

    def __getattribute__(self, item):
        # todo: to replace this code with switchable views asap
        if item == 'contents':
            if self.context['object'].appliance.version >= '5.7':
                view_type = self.toolbar.view_selector.selected
                if view_type == 'Summary View':
                    return ProviderDetailsSummaryView(parent=self)

                elif view_type == 'Dashboard View':
                    return ProviderDetailsDashboardView(parent=self)

                else:
                    raise Exception('The content view type "{v}" for provider "{p}" doesnt '
                                    'exist'.format(v=view_type, p=self.context['object'].name))
            else:
                return ProviderDetailsSummaryView(parent=self)  # 5.6 has only only Summary view

        else:
            return super(ProviderDetailsView, self).__getattribute__(item)

    @property
    def is_displayed(self):
        if self.context['object'].appliance.version >= '5.7':
            subtitle = 'Summary' if self.toolbar.view_selector.selected == 'Summary View' \
                else 'Dashboard'
        else:
            subtitle = 'Summary'  # 5.6 has only only Summary view
        title = '{name} ({subtitle})'.format(name=self.context['object'].name, subtitle=subtitle)

        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.breadcrumb.active_location == title


class ProviderTimelinesView(TimelinesView, BaseLoggedInPage):
    """
     represents Timelines page
    """
    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] \
            and TimelinesView.is_displayed


class ProvidersDiscoverView(BaseLoggedInPage):
    """
     Discover View from Infrastructure Providers page
    """
    title = Text('//div[@id="main-content"]//h1')

    vmware = Checkbox('discover_type_virtualcenter')
    scvmm = Checkbox('discover_type_scvmm')
    rhevm = Checkbox('discover_type_rhevm')

    from_ip1 = Input('from_first')
    from_ip2 = Input('from_second')
    from_ip3 = Input('from_third')
    from_ip4 = Input('from_fourth')
    to_ip4 = Input('to_fourth')

    start = Button('Start')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.title.text == 'Infrastructure Providers Discovery'


class ProvidersManagePoliciesView(BaseLoggedInPage):
    """
     Provider's Manage Policies view
    """
    policies = VersionPick({Version.lowest(): DynaTree('protect_treebox'),
                            '5.7': BootstrapTreeview('protectbox')})
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class ProvidersEditTagsView(BaseLoggedInPage):
    """
     Provider's Edit Tags view
    """
    tag_category = BootstrapSelect('tag_cat')
    tag = BootstrapSelect('tag_add')
    chosen_tags = Table(locator='//div[@id="assignments_div"]/table')

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class NodesToolBar(View):
    """
     represents nodes toolbar and its controls (exists for Infra OpenStack provider)
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    power = Dropdown(text='Power')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ProviderRegisterNodesView(View):
    """
     represents Register Nodes view (exists for Infra OpenStack provider)
    """
    file = FileInput(locator='//input[@id="nodes_json_file"]')
    register = Button('Register')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class ProviderNodesView(BaseLoggedInPage):
    """
     represents main Nodes view (exists for Infra OpenStack provider)
    """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(NodesToolBar)
    contents = View.nested(View)  # left it for future
    paginator = View.nested(PaginationPane)

    @property
    def is_displayed(self):
        title = '{name} (All Managed Hosts)'.format(name=self.context['object'].name)
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.title.text == title


class ProviderToolBar(View):
    """
     represents provider toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ProviderEntities(View):
    """
    should represent the view with different items like providers
    """
    title = Text('//div[@id="main-content"]//h1')
    search = View.nested(Search)
    # todo: in progress


class ProviderSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    pass


class ProvidersView(BaseLoggedInPage):
    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.entities.title.text == 'Infrastructure Providers'

    toolbar = View.nested(ProviderToolBar)
    sidebar = View.nested(ProviderSideBar)
    entities = View.nested(ProviderEntities)
    paginator = View.nested(PaginationPane)
