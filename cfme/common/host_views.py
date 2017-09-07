# -*- coding: utf-8 -*-
from widgetastic.utils import (
    Parameter,
    ParametrizedLocator,
    Version,
    VersionPick
)
from widgetastic.widget import ParametrizedView, Text, View
from widgetastic_manageiq import (
    BaseEntitiesView,
    NonJSBaseEntity,
    JSBaseEntity,
    BaseListEntity,
    BaseQuadIconEntity,
    BaseTileIconEntity,
    BootstrapTreeview,
    BreadCrumb,
    Button,
    Checkbox,
    Input,
    ItemsToolBarViewSelector,
    PaginationPane,
    SummaryTable,
    Table,
    TimelinesView,
    BaseNonInteractiveEntitiesView
)
from widgetastic_patternfly import (
    BootstrapSelect,
    CheckableBootstrapTreeview,
    Dropdown,
    FlashMessages,
    Tab
)

from cfme.base.login import BaseLoggedInPage


class ComputeInfrastructureHostsView(BaseLoggedInPage):
    """Common parts for host views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')
    flash = FlashMessages(
        './/div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
        'contains(@class, "flash_text_div")]'
    )

    @property
    def in_compute_infrastructure_hosts(self):
        def _host_page(title):
            return self.navigation.currently_selected == ["Compute", "Infrastructure", title]

        return (
            self.logged_in_as_current_user and (_host_page("Hosts") or _host_page("Nodes") or
                                                _host_page("Hosts / Nodes"))
        )


class HostQuadIconEntity(BaseQuadIconEntity):
    @property
    def data(self):
        return {
            'no_vm': int(self.browser.text(self.QUADRANT.format(pos="a"))),
            'state': self.browser.get_attribute("style", self.QUADRANT.format(pos="b")),
            'vendor': self.browser.get_attribute("alt", self.QUADRANT.format(pos="c")),
            'creds': self.browser.get_attribute("alt", self.QUADRANT.format(pos="d"))
        }


class HostTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(HostQuadIconEntity)


class HostListEntity(BaseListEntity):
    pass


class NonJSHostEntity(NonJSBaseEntity):
    quad_entity = HostQuadIconEntity
    list_entity = HostListEntity
    tile_entity = HostTileIconEntity


def HostEntity():  # noqa
    """ Temporary wrapper for Host Entity during transition to JS based Entity

    """
    return VersionPick({
        Version.lowest(): NonJSHostEntity,
        '5.9': JSBaseEntity,
    })


class HostDetailsToolbar(View):
    """Represents host toolbar and its controls."""
    monitoring = Dropdown(text="Monitoring")
    configuration = Dropdown(text="Configuration")
    policy = Dropdown(text="Policy")
    power = Dropdown(text="Power")

    @ParametrizedView.nested
    class custom_button(ParametrizedView):  # noqa
        PARAMETERS = ("button_group", )
        _dropdown = Dropdown(text=Parameter("button_group"))

        def item_select(self, button, handle_alert=False):
            self._dropdown.item_select(button, handle_alert=handle_alert)


class HostDetailsEntities(View):
    """Represents Details page."""
    properties = SummaryTable(title="Properties")
    relationships = SummaryTable(title="Relationships")
    compliance = SummaryTable(title="Compliance")
    configuration = SummaryTable(title="Configuration")
    smart_management = SummaryTable(title="Smart Management")
    security = SummaryTable(title="Security")
    authentication_status = SummaryTable(title="Authentication Status")
    openstack_hardware = SummaryTable(title="Openstack Hardware")


class HostDetailsView(ComputeInfrastructureHostsView):
    """Main Host details page."""
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    toolbar = View.nested(HostDetailsToolbar)
    entities = View.nested(HostDetailsEntities)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return self.in_compute_infrastructure_hosts and self.breadcrumb.active_location == title


class HostDriftHistory(ComputeInfrastructureHostsView):
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    history_table = Table(locator='.//div[@id="main_div"]/table')
    analyze_button = Button(title="Select up to 10 timestamps for Drift Analysis")

    @property
    def is_displayed(self):
        return (
            self.in_compute_infrastructure_hosts and
            self.title.text == "Drift History" and
            self.history_table.is_displayed
        )


class HostDriftAnalysis(ComputeInfrastructureHostsView):
    apply_button = Button("Apply")
    drift_sections = CheckableBootstrapTreeview(tree_id="all_sectionsbox")

    @ParametrizedView.nested
    class drift_analysis(ParametrizedView):  # noqa
        PARAMETERS = ("drift_section", )
        CELLS = "../td//i"
        row = Text(ParametrizedLocator(".//div[@id='compare-grid']/"
                                       "/th[normalize-space(.)={drift_section|quote}]"))

        @property
        def is_changed(self):
            cells = self.browser.elements(self.CELLS, parent=self.row)
            attrs = [self.browser.get_attribute("class", cell) for cell in cells]
            return "drift-delta" in attrs

    @View.nested
    class toolbar(View):  # noqa
        all_attributes = Button(title="All attributes")
        different_values_attributes = Button(title="Attributes with different")
        same_values_attributes = Button(title="Attributes with same values")
        details_mode = Button(title="Details Mode")
        exists_mode = Button(title="Exists Mode")

    @property
    def is_displayed(self):
        return (
            self.in_compute_infrastructure_hosts and
            self.title.text == "'{}' Drift Analysis".format(self.context["object"].name)
        )


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

    start_button = Button("Start")
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and self.title.text == "Hosts / Nodes Discovery"


class HostManagePoliciesView(BaseLoggedInPage):
    """Host's Manage Policies view."""
    policies = BootstrapTreeview("protectbox")
    entities = View.nested(BaseNonInteractiveEntitiesView)
    save_button = Button("Save")
    reset_button = Button("Reset")
    cancel_button = Button("Cancel")

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


class HostSideBar(View):
    """Represents left side bar. It usually contains navigation, filters, etc."""
    pass


class HostEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""
    @property
    def entity_class(self):
        return HostEntity().pick(self.browser.product_version)


class HostsView(ComputeInfrastructureHostsView):
    toolbar = View.nested(HostsToolbar)
    sidebar = View.nested(HostSideBar)
    paginator = PaginationPane()
    including_entities = View.include(HostEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and self.title.text in "Hosts / Nodes"


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
    """View for editing a single host"""
    save_button = Button("Save")
    reset_button = Button("Reset")
    change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and self.title.text == "Info/Settings"


class HostsEditView(HostEditView):
    """View when editing multiple hosts
        Restricted to endpoints section of the form
        Title changes
        Must select host before validation
    """
    validation_host = BootstrapSelect('validate_id')  # only shown when editing multiple hosts

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and self.title.text == 'Credentials/Settings'
