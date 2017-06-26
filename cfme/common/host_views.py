# -*- coding: utf-8 -*-
from widgetastic.widget import ParametrizedView, Text, View
from widgetastic_patternfly import BootstrapSelect, Dropdown, FlashMessages, Tab

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ItemNotFound, ManyItemsFound
from widgetastic_manageiq import (
    BaseItem,
    BaseListItem,
    BaseQuadIconItem,
    BaseTileIconItem,
    BootstrapTreeview,
    BreadCrumb,
    Button,
    Checkbox,
    Input,
    ItemsToolBarViewSelector,
    PaginationPane,
    Search,
    SummaryTable,
    Table,
    TimelinesView
)


class ComputeInfrastructureHostsView(BaseLoggedInPage):
    """Common parts for host views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')
    flash = FlashMessages(
        './/div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
        'contains(@class, "flash_text_div")]'
    )

    @property
    def in_compute_infrastructure_hosts(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Hosts"]
        )


class HostQuadIconItem(BaseQuadIconItem):
    @property
    def data(self):
        br = self.browser
        return {
            "vms_number": br.text(self.QUADRANT.format(pos="a")),
            "status": br.get_attribute("style", self.QUADRANT.format(pos="b")),
            "vendor": br.get_attribute("src", self.QUADRANT.format(pos="c")),
            "creds": br.get_attribute("src", self.QUADRANT.format(pos="d")),
        }


class HostTileIconItem(BaseTileIconItem):
    quad_icon = ParametrizedView.nested(HostQuadIconItem)


class HostListItem(BaseListItem):
    pass


class HostItem(BaseItem):
    quad_item = HostQuadIconItem
    list_item = HostListItem
    tile_item = HostTileIconItem


class HostDetailsToolbar(View):
    """Represents host toolbar and its controls."""
    monitoring = Dropdown(text="Monitoring")
    configuration = Dropdown(text="Configuration")
    policy = Dropdown(text="Policy")
    power = Dropdown(text="Power")


class HostDetailsSummaryView(View):
    """Represents Details page."""
    properties = SummaryTable(title="Properties")
    relationships = SummaryTable(title="Relationships")
    compliance = SummaryTable(title="Compliance")
    configuration = SummaryTable(title="Configuration")
    smart_management = SummaryTable(title="Smart Management")
    authentication_status = SummaryTable(title="Authentication Status")


class HostDetailsView(ComputeInfrastructureHostsView):
    """Main Host details page."""
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    toolbar = View.nested(HostDetailsToolbar)
    contents = View.nested(HostDetailsSummaryView)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return self.in_compute_infrastructure_hosts and self.breadcrumb.active_location == title


class HostTimelinesView(TimelinesView, ComputeInfrastructureHostsView):
    """Represents a Host Timelines page."""

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and super(TimelinesView, self).is_displayed


class HostDiscoverView(ComputeInfrastructureHostsView):
    """Discover View from Compute/Infrastructure/Hosts page."""
    esx = Checkbox(name="discover_type_esx")
    ipmi = Checkbox(name="discover_type_ipmi")

    from_ip1 = Input(name="from_first")
    from_ip2 = Input(name="from_second")
    from_ip3 = Input(name="from_third")
    from_ip4 = Input(name="from_fourth")
    to_ip4 = Input(name="to_fourth")

    start = Button("Start")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and self.title.text == "Hosts / Nodes Discovery"


class HostManagePoliciesView(BaseLoggedInPage):
    """Host's Manage Policies view."""
    policies = BootstrapTreeview("protectbox")
    save = Button("Save")
    reset = Button("Reset")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return False


class HostEditTagsView(BaseLoggedInPage):
    """Host's Edit Tags view."""
    tag_category = BootstrapSelect("tag_cat")
    tag = BootstrapSelect("tag_add")
    chosen_tags = Table(locator='.//div[@id="assignments_div"]/table')

    save = Button("Save")
    reset = Button("Reset")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return False


class HostsToolbar(View):
    """Represents hosts toolbar and its controls."""
    configuration = Dropdown(text="Configuration")
    policy = Dropdown(text="Policy")
    lifecycle = Dropdown(text="Lifecycle")
    monitoring = Dropdown(text="Monitoring")
    power = Dropdown(text="Power")
    view_selector = View.nested(ItemsToolBarViewSelector)


class HostItems(View):
    """Represents the view with different items like hosts."""
    search = View.nested(Search)
    _quadicons = './/tr[./td/div[@class="quadicon"]]/following-sibling::tr/td/a'
    _listitems = Table(locator='.//div[@id="list_grid"]/table')

    def _get_item_names(self):
        if self.parent.toolbar.view_selector.selected == "List View":
            return [row.name.text for row in self._listitems.rows()]
        else:
            br = self.browser
            return [br.get_attribute("title", el) for el in br.elements(self._quadicons)]

    def get_all(self, surf_pages=False):
        """Obtains all items like QuadIcon displayed by view.

        Args:
            surf_pages (bool): current page items if False, all items otherwise

        Returns: all items (QuadIcon/etc.) displayed by view
        """
        if not surf_pages:
            return [HostItem(parent=self, name=name) for name in self._get_item_names()]
        else:
            items = []
            for _ in self.parent.paginator.pages():
                items.extend([HostItem(parent=self, name=name) for name in self._get_item_names()])
            return items

    def get_items(self, by_name=None, surf_pages=False):
        """Obtains all matched items like QuadIcon displayed by view.

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
        """Obtains one item matched to by_name. Raises exception if no items or several items were
           found.

        Args:
            by_name (str): only item which match to by_name will be returned
            surf_pages (bool): current page items if False, all items otherwise

        Returns: matched item (QuadIcon/etc.)
        """
        items = self.get_items(by_name=by_name, surf_pages=surf_pages)
        if not items:
            raise ItemNotFound("Item {name} isn't found on this page".format(name=by_name))
        elif len(items) > 1:
            raise ManyItemsFound("Several items with {name} were found".format(name=by_name))
        return items[0]


class HostSideBar(View):
    """Represents left side bar. It usually contains navigation, filters, etc."""
    pass


class HostsView(ComputeInfrastructureHostsView):
    toolbar = View.nested(HostsToolbar)
    sidebar = View.nested(HostSideBar)
    items = View.nested(HostItems)
    paginator = View.nested(PaginationPane)

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and self.items.title.text == "Hosts"


class HostFormView(ComputeInfrastructureHostsView):
    # Info/Settings
    title = Text(".//div[@id='main-content']//h1")
    name = Input(name="name")
    hostname = Input(name="hostname")
    custom_ident = Input(name="custom_1")
    ipmi_address = Input(name="ipmi_address")
    mac_address = Input(name="mac_address")

    @View.nested
    class endpoints(View):  # noqa
        @View.nested
        class default(Tab):  # noqa
            username = Input(name="default_userid")
            password = Input(name="default_password")
            confirm_password = Input(name="default_verify")
            validate_button = Button("Validate")

        @View.nested
        class remote_login(Tab):  # noqa
            TAB_NAME = "Remote Login"
            username = Input(name="remote_userid")
            password = Input(name="remote_password")
            confirm_password = Input(name="remote_verify")
            validate_button = Button("Validate")

        @View.nested
        class web_services(Tab):  # noqa
            TAB_NAME = "Web Services"
            username = Input(name="ws_userid")
            password = Input(name="ws_password")
            confirm_password = Input(name="ws_verify")
            validate_button = Button("Validate")

        @View.nested
        class ipmi(Tab):  # noqa
            TAB_NAME = "IPMI"
            username = Input(name="ipmi_userid")
            password = Input(name="ipmi_password")
            confirm_password = Input(name="ipmi_verify")
            validate_button = Button("Validate")

    cancel_button = Button("Cancel")


class HostAddView(HostFormView):
    host_platform = BootstrapSelect("user_assigned_os")
    add_button = Button("Add")
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and self.title.text == "Add New Host"


class HostEditView(HostFormView):
    save_button = Button("Save")
    reset_button = Button("Reset")
    change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and self.title.text == "Info/Settings"
