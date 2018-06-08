# -*- coding: utf-8 -*-
from lxml.html import document_fromstring
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import (
    Parameter,
    Version,
    VersionPick
)
from widgetastic.widget import ParametrizedView, Text, View
from widgetastic_patternfly import (
    BootstrapNav,
    BootstrapSelect,
    CheckableBootstrapTreeview,
    Dropdown,
    Tab,
)

from cfme.base.login import BaseLoggedInPage
from widgetastic_manageiq import (
    Accordion,
    BaseEntitiesView,
    BaseListEntity,
    BaseQuadIconEntity,
    BaseTileIconEntity,
    BreadCrumb,
    Button,
    Checkbox,
    DriftComparison,
    Input,
    ItemsToolBarViewSelector,
    JSBaseEntity,
    ManageIQTree,
    NonJSBaseEntity,
    PaginationPane,
    ParametrizedSummaryTable,
    Table,
    TimelinesView
)


class ComputeInfrastructureHostsView(BaseLoggedInPage):
    """Common parts for host views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

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
        try:
            return {
                'no_vm': int(self.browser.text(self.QUADRANT.format(pos="a"))),
                'state': self.browser.get_attribute("style", self.QUADRANT.format(pos="b")),
                'vendor': self.browser.get_attribute("alt", self.QUADRANT.format(pos="c")),
                'creds': self.browser.get_attribute("alt", self.QUADRANT.format(pos="d"))
            }
        except (IndexError, NoSuchElementException):
            return {}


class HostTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(HostQuadIconEntity)


class HostListEntity(BaseListEntity):
    pass


class NonJSHostEntity(NonJSBaseEntity):
    quad_entity = HostQuadIconEntity
    list_entity = HostListEntity
    tile_entity = HostTileIconEntity


class JSHostEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(JSHostEntity, self).data
        try:
            if 'quadicon' in data_dict and data_dict['quadicon']:
                quad_data = document_fromstring(data_dict['quadicon'])
                data_dict['no_vm'] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
                data_dict['state'] = quad_data.xpath(self.QUADRANT.format(pos="b"))[0].get('style')
                data_dict['vendor'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].get('alt')
                data_dict['creds'] = quad_data.xpath(self.QUADRANT.format(pos="d"))[0].get('alt')
            return data_dict
        except (IndexError, TypeError):
            return {}


def HostEntity():  # noqa
    """ Temporary wrapper for Host Entity during transition to JS based Entity

    """
    return VersionPick({
        Version.lowest(): NonJSHostEntity,
        '5.9': JSHostEntity,
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
    summary = ParametrizedView.nested(ParametrizedSummaryTable)


class HostDetailsView(ComputeInfrastructureHostsView):
    """Main Host details page."""
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    toolbar = View.nested(HostDetailsToolbar)
    entities = View.nested(HostDetailsEntities)

    @View.nested
    class security_accordion(Accordion):  # noqa
        ACCORDION_NAME = "Security"

        navigation = BootstrapNav('.//div/ul')

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
    drift_analysis = DriftComparison(locator=".//div[@id='compare-grid']")

    @View.nested
    class toolbar(View):  # noqa
        all_attributes = Button(title="All attributes")
        different_values_attributes = Button(title="Attributes with different values")
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
    breadcrumb = BreadCrumb()

    @property
    def is_displayed(self):
        return (
            self.in_compute_infrastructure_hosts and
            '{} (Summary)'.format(self.context['object'].name) in self.breadcrumb.locations and
            self.is_timelines)


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


class HostsToolbar(View):
    """Represents hosts toolbar and its controls."""
    configuration = Dropdown(text="Configuration")
    policy = Dropdown(text="Policy")
    lifecycle = Dropdown(text="Lifecycle")
    monitoring = Dropdown(text="Monitoring")
    power = Dropdown(text="Power")
    view_selector = View.nested(ItemsToolBarViewSelector)


class HostEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""
    @property
    def entity_class(self):
        return HostEntity().pick(self.browser.product_version)


class HostsView(ComputeInfrastructureHostsView):
    toolbar = View.nested(HostsToolbar)

    @View.nested
    class filters(Accordion):  # noqa
        ACCORDION_NAME = "Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()

    default_filter_btn = Button(title="Set the current filter as my default")
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
            change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")
            username = Input(name="default_userid")
            password = Input(name="default_password")
            confirm_password = Input(name="default_verify")
            validate_button = Button("Validate")

        @View.nested
        class remote_login(Tab):  # noqa
            TAB_NAME = "Remote Login"
            change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")
            username = Input(name="remote_userid")
            password = Input(name="remote_password")
            confirm_password = Input(name="remote_verify")
            validate_button = Button("Validate")

        @View.nested
        class web_services(Tab):  # noqa
            TAB_NAME = "Web Services"
            change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")
            username = Input(name="ws_userid")
            password = Input(name="ws_password")
            confirm_password = Input(name="ws_verify")
            validate_button = Button("Validate")

        @View.nested
        class ipmi(Tab):  # noqa
            TAB_NAME = "IPMI"
            change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")
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
    breadcrumb = BreadCrumb()
    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return False


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


class ProviderAllHostsView(HostsView):
    """
    This view is used in test_provider_relationships
    """

    @property
    def is_displayed(self):
        return (
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Providers"] and
            self.title.text == "{} (All Managed Hosts)".format(self.context["object"].name)
        )
