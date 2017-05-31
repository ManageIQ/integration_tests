# -*- coding: utf-8 -*-
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View, Text
from widgetastic_patternfly import Dropdown, BootstrapSelect

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ItemNotFound, ManyItemsFound
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
                                  BootstrapTreeview,
                                  ProviderItem)


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


class ProviderItems(View):
    """
    should represent the view with different items like providers
    """
    title = Text('//div[@id="main-content"]//h1')
    search = View.nested(Search)
    _quadicons = '//tr[./td/div[@class="quadicon"]]/following-sibling::tr/td/a'
    _listitems = Table(locator='//div[@id="list_grid"]/table')

    def _get_item_names(self):
        if self.parent.toolbar.view_selector.selected == 'List View':
            return [row.name.text for row in self._listitems.rows()]
        else:
            br = self.browser
            return [br.get_attribute('title', el) for el in br.elements(self._quadicons)]

    def get_all(self, surf_pages=False):
        """
        obtains all items like QuadIcon displayed by view
        Args:
            surf_pages (bool): current page items if False, all items otherwise

        Returns: all items (QuadIcon/etc.) displayed by view
        """
        if not surf_pages:
            return [ProviderItem(parent=self, name=name) for name in self._get_item_names()]
        else:
            items = []
            for _ in self.parent.paginator.pages():
                items.extend([ProviderItem(parent=self, name=name)
                              for name in self._get_item_names()])
            return items

    def get_items(self, by_name=None, surf_pages=False):
        """
        obtains all matched items like QuadIcon displayed by view
        Args:
            by_name (str): only items which match to by_name will be returned
            surf_pages (bool): current page items if False, all items otherwise

        Returns: all matched items (QuadIcon/etc.) displayed by view
        """
        items = self.get_all(surf_pages)
        remaining_items = []
        for item in items:
            if by_name and by_name in item.name:
                remaining_items.append(item)
            # todo: by_type and by_regexp will be implemented later if needed
        return remaining_items

    def get_item(self, by_name=None, surf_pages=False):
        """
        obtains one item matched to by_name
        raises exception if no items or several items were found
        Args:
            by_name (str): only item which match to by_name will be returned
            surf_pages (bool): current page items if False, all items otherwise

        Returns: matched item (QuadIcon/etc.)
        """
        items = self.get_items(by_name=by_name, surf_pages=surf_pages)
        if len(items) == 0:
            raise ItemNotFound("Item {name} isn't found on this page".format(name=by_name))
        elif len(items) > 1:
            raise ManyItemsFound("Several items with {name} were found".format(name=by_name))
        return items[0]


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
    items = View.nested(ProviderItems)
    paginator = View.nested(PaginationPane)


class BeforeFillMixin(object):
    def before_fill(self):
        if self.exists and not self.is_active():
            self.select()


class ProviderAddView(BaseLoggedInPage):
    title = Text('//div[@id="main-content"]//h1')
    name = Input('name')
    prov_type = BootstrapSelect(id='emstype')
    api_version = BootstrapSelect(id='api_version')  # only for OpenStack
    zone = Input('zone')

    add = Button('Add')
    cancel = Button('Cancel')

    @View.nested
    class endpoints(View):  # NOQA
        # this is switchable view that gets replaced with concrete view.
        # it gets changed according to currently chosen provider type
        # look at cfme.common.provider.BaseProvider.create() method
        pass

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.title.text == 'Add New Infrastructure Provider'


class ProviderEditView(ProviderAddView):
    prov_type = Text(locator='//label[@name="emstype"]')

    # only in edit view
    vnc_start_port = Input('host_default_vnc_port_start')
    vnc_end_port = Input('host_default_vnc_port_end')

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.title.text == 'Edit Infrastructure Provider'
