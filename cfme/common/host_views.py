from lxml.html import document_fromstring
from widgetastic.utils import Parameter
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import CheckableBootstrapTreeview
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common import CompareView
from cfme.common import TimelinesView
from cfme.exceptions import displayed_not_implemented
from cfme.utils.log import logger
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import Button
from widgetastic_manageiq import Checkbox
from widgetastic_manageiq import DriftComparison
from widgetastic_manageiq import Input
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import JSBaseEntity
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import ParametrizedSummaryTable
from widgetastic_manageiq import Search
from widgetastic_manageiq import Table
from widgetastic_manageiq import WaitTab


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


class HostEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super().data
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


class HostDetailsToolbar(View):
    """Represents host toolbar and its controls."""
    monitoring = Dropdown(text="Monitoring")
    configuration = Dropdown(text="Configuration")
    policy = Dropdown(text="Policy")
    power = Dropdown(text="Power")
    download = Button(title='Print or export summary')

    @ParametrizedView.nested
    class custom_button(ParametrizedView):  # noqa
        PARAMETERS = ("button_group", )
        _dropdown = Dropdown(text=Parameter("button_group"))

        def item_select(self, button, handle_alert=False):
            self._dropdown.item_select(button, handle_alert=handle_alert)


class HostDetailsEntities(View):
    """Represents Details page."""
    summary = ParametrizedView.nested(ParametrizedSummaryTable)


class HostNetworkDetailsView(View):
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    network_tree = BootstrapNav(".//div[contains(@class,'treeview')]/ul")

    @property
    def is_displayed(self):
        return (self.network_tree.is_displayed and
        "{} (Network)".format(self.context["object"].name) == self.breadcrumb.active_location)


class HostDetailsAccordionView(View):

    @View.nested
    class properties(Accordion):  # noqa
        ACCORDION_NAME = "Properties"
        tree = BootstrapNav(locator='//div[@id="host_prop"]//ul')

    @View.nested
    class relationships(Accordion):  # noqa
        ACCORDION_NAME = "Relationships"
        tree = BootstrapNav(locator='//div[@id="host_rel"]//ul')

    @View.nested
    class security(Accordion):  # noqa
        ACCORDION_NAME = "Security"
        tree = BootstrapNav(locator='//div[@id="host_sec"]//ul')

    @View.nested
    class configuration(Accordion):  # noqa
        ACCORDION_NAME = "Configuration"
        tree = BootstrapNav(locator='//div[@id="host_config"]//ul')


class HostDetailsView(ComputeInfrastructureHostsView):
    """Main Host details page."""
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    toolbar = View.nested(HostDetailsToolbar)
    entities = View.nested(HostDetailsEntities)
    sidebar = View.nested(HostDetailsAccordionView)

    @property
    def is_displayed(self):
        return (
            self.in_compute_infrastructure_hosts and
            self.breadcrumb.active_location == self.context["object"].expected_details_breadcrumb
        )


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
    pass


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
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class HostEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""
    @property
    def entity_class(self):
        return HostEntity


class HostPrintView(BaseLoggedInPage):
    pass


class HostsView(ComputeInfrastructureHostsView):
    toolbar = View.nested(HostsToolbar)

    @View.nested
    class filters(Accordion):  # noqa
        ACCORDION_NAME = VersionPicker({
            Version.lowest(): 'Filters',
            '5.11': 'Global Filters'
        })

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()

    default_filter_btn = Button(title="Set the current filter as my default")
    paginator = PaginationPane()
    search = View.nested(Search)
    including_entities = View.include(HostEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return self.in_compute_infrastructure_hosts and "Hosts" in self.title.text


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
        class default(WaitTab):  # noqa
            change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")
            username = Input(name="default_userid")
            password = Input(name="default_password")
            confirm_password = Input(name="default_verify")
            validate_button = Button("Validate")

        @View.nested
        class remote_login(WaitTab):  # noqa
            TAB_NAME = "Remote Login"
            change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")
            username = Input(name="remote_userid")
            password = Input(name="remote_password")
            confirm_password = Input(name="remote_verify")
            validate_button = Button("Validate")

        @View.nested
        class web_services(WaitTab):  # noqa
            TAB_NAME = "Web Services"
            change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")
            username = Input(name="ws_userid")
            password = Input(name="ws_password")
            confirm_password = Input(name="ws_verify")
            validate_button = Button("Validate")

        @View.nested
        class ipmi(WaitTab):  # noqa
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
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        return (
            self.in_compute_infrastructure_hosts and self.navigation.currently_selected == [
                'Compute', 'Infrastructure', 'Hosts'] and self.title.text == 'Info/Settings')


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


class HostsCompareView(CompareView, ComputeInfrastructureHostsView):
    """Compare Host / Node page."""

    @property
    def is_displayed(self):
        title = "Compare Host / Node"
        return (self.logged_in_as_current_user and
                self.title.text == title and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Hosts']
                )


class ProviderHostsCompareView(HostsCompareView):
    """Compare Host / Node page, but for a specific provider."""
    @property
    def is_displayed(self):
        title = "Compare Host / Node"
        return (self.logged_in_as_current_user and
                self.title.text == title and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers']
                )


class ProviderAllHostsView(HostsView):
    """
    This view is used in Provider and HostCollection contexts
    """

    @property
    def is_displayed(self):
        """Accounts for both Provider and HostCollection contexts"""
        from cfme.modeling.base import BaseEntity, BaseCollection
        expected_title = "{} (All Managed Hosts)"
        obj = self.context['object']
        is_entity = getattr(obj, 'name', False) and isinstance(obj, BaseEntity)
        is_filtered = isinstance(obj, BaseCollection) and obj.filters  # empty dict on not filtered
        filter = obj.filters.get('parent') or obj.filters.get('provider') if is_filtered else None

        # could condense the following logic in a more pythonic way, but would lose the logging
        if is_entity:
            # object has name attribute and is BaseEntity derived, assuming its a provider
            logger.debug('Hosts view context object is assumed to be provider: %r', obj)
            matched_title = self.title.text == expected_title.format(obj.name)
        elif filter and hasattr(filter, 'name'):
            # filtered collection, use filter object's name
            logger.debug(
                'Hosts view context object has filter related to view with name attribute: %r',
                obj.filters
            )
            matched_title = self.title.text == expected_title.format(filter.name)
        else:
            matched_title = False  # not an entity with a name, or a filtered collection

        return (
            matched_title and
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers']
        )


class HostDevicesView(HostsView):
    """The devices page"""

    @property
    def is_displayed(self):
        active_loc = f"{self.context['object'].name} (Devices)"
        return self.breadcrumb.active_location == active_loc


class HostOsView(HostsView):
    """The Operating System page"""

    @property
    def is_displayed(self):
        active_loc = f"{self.context['object'].name} (OS Information)"
        return self.breadcrumb.active_location == active_loc


class HostStorageAdaptersView(HostsView):
    """The storage adapters page"""
    # Work on the title locator or another better way to do is_displayed.
    @property
    def is_displayed(self):
        active_loc = f"{self.context['object'].name} (Storage Adapters)"
        return self.breadcrumb.active_location == active_loc


class HostServicesView(HostsView):
    """The services page"""

    @property
    def is_displayed(self):
        active_loc = f"{self.context['object'].name} (Services)"
        return self.breadcrumb.active_location == active_loc


class HostVmmInfoView(HostsView):
    """The VM monitor info page"""
    # Work on the title locator or another better way to do is_displayed.
    @property
    def is_displayed(self):
        active_loc = f"{self.context['object'].name} (VM Monitor Information)"
        return self.breadcrumb.active_location == active_loc


class RegisteredHostsView(HostsView):
    """
    represents Hosts related to some datastore
    """
    is_displayed = displayed_not_implemented
