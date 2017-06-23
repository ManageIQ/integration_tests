""" A model of an Infrastructure Host in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var credentials_form: A :py:class:`cfme.web_ui.Form` object describing the credentials form.
"""

from functools import partial
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_patternfly import Dropdown, Tab, Button, BootstrapSelect
from widgetastic.widget import Text, Input, View
from selenium.common.exceptions import NoSuchElementException

from cfme.base.login import BaseLoggedInPage
from cfme.base.credential import Credential as BaseCredential
from cfme.exceptions import HostNotFound
from utils.ipmi import IPMI
from utils.log import logger
from utils.update import Updateable
from utils.wait import wait_for
from utils import deferred_verpick, version, conf
from utils.pretty import Pretty
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.appliance import Navigatable
from widgetastic_manageiq import TimelinesView, PaginationPane, SummaryTable

from cfme.common import PolicyProfileAssignable

# Page specific locators

manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")

drift_table = CheckboxTable({
    version.LOWEST: "//table[@class='style3']",
    "5.4": "//th[normalize-space(.)='Timestamp']/ancestor::table[1]"
})

host_add_btn = {
    version.LOWEST: FormButton('Add this Host'),
    "5.5": FormButton("Add")
}
default_host_filter_btn = FormButton('Set the current filter as my default')


class HostToolBar(View):
    """
    represents host toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')
    lifecycle = Dropdown(text='Lifecycle')
    power = Dropdown(text='Power Operations')

    view_selector = View.nested(ItemsToolBarViewSelector)


class HostSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    @View.nested
    class filters(Accordion):  # noqa
        ACCORDION_NAME = "Filters"
        tree = ManageIQTree()


class HostEntities(BaseEntitiesView):
    """
    represents central view where all QuadIcons, etc are displayed
    """
    pass


class HostsView(BaseLoggedInPage):
    """
    represents whole All Hosts page
    """
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    toolbar = View.nested(HostToolBar)
    sidebar = View.nested(HostSideBar)
    including_entities = View.include(HostEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure',
                                                       'Hosts'] and
                self.entities.title.text == 'Hosts')


class InfraHostTimelinesView(TimelinesView, BaseLoggedInPage):

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure', '/host'] and
            super(TimelinesView, self).is_displayed
        )


class CommonToolbar(View):
    configuration = Dropdown("Configuration")
    policy = Dropdown("Policy")
    lifecycle = Dropdown("Lifecycle")
    power = Dropdown("Power")


class InfraHostsAllView(BaseLoggedInPage):
    title = Text(".//div[@id='main-content']//h1")
    pagination_pane = PaginationPane()

    @View.nested
    class toolbar(CommonToolbar):
        grid_view_button = Button(title="Grid View")
        tile_view_button = Button(title="Tile View")
        list_view_button = Button(title="List View")

    @property
    def is_displayed(self):
        return self.title.text == "Hosts"


class InfraHostDetailsView(BaseLoggedInPage):
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')
    toolbar = CommonToolbar()

    @View.nested
    class summary(View):  # noqa
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        compliance = SummaryTable(title="Compliance")
        configuration = SummaryTable(title="Configuration")
        smart_management = SummaryTable(title="Smart Management")
        authentication_status = SummaryTable(title="Authentication Status")

    @property
    def is_displayed(self):
        return self.title.text == "{} (Summary)".format(self.context["object"].name)


class InfraHostFormView(BaseLoggedInPage):
    # Info/Settings
    title = Text(".//div[@id='main-content']//h1")
    name = Input(name="name")
    hostname = Input(name="hostname")
    custom_ident = Input(name="custom_1")
    ipmi_address = Input(name="ipmi_address")
    mac_address = Input(name="mac_address")

    # Endpoints
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


class InfraHostAddView(InfraHostFormView):
    host_platform = BootstrapSelect("user_assigned_os")
    add_button = Button("Add")
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        return self.title.text == "Add New Host"


class InfraHostEditView(InfraHostFormView):
    save_button = Button("Save")
    reset_button = Button("Reset")
    change_stored_password = Text(".//a[contains(@ng-hide, 'bChangeStoredPassword')]")

    @property
    def is_displayed(self):
        return self.title.text == "Info/Settings"


class Host(Updateable, Pretty, Navigatable, PolicyProfileAssignable):
    """
    Model of an infrastructure host in cfme.

    Args:
        name: Name of the host.
        hostname: Hostname of the host.
        ip_address: The IP address as a string.
        custom_ident: The custom identifiter.
        host_platform: Included but appears unused in CFME at the moment.
        ipmi_address: The IPMI address.
        mac_address: The mac address of the system.
        credentials (:py:class:`Credential`): see Credential inner class.
        ipmi_credentials (:py:class:`Credential`): see Credential inner class.

    Usage:

        myhost = Host(name='vmware',
                      credentials=Provider.Credential(principal='admin', secret='foobar'))
        myhost.create()

    """
    pretty_attrs = ['name', 'hostname', 'ip_address', 'custom_ident']

    def __init__(self, name=None, hostname=None, ip_address=None, custom_ident=None,
                 host_platform=None, ipmi_address=None, mac_address=None, credentials=None,
                 ipmi_credentials=None, interface_type='lan', provider=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.quad_name = 'host'
        self.hostname = hostname
        self.ip_address = ip_address
        self.custom_ident = custom_ident
        self.host_platform = host_platform
        self.ipmi_address = ipmi_address
        self.mac_address = mac_address
        self.credentials = credentials
        self.ipmi_credentials = ipmi_credentials
        self.interface_type = interface_type
        self.db_id = None
        self.provider = provider

    class Credential(BaseCredential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using IPMI type credential, ipmi = True"""

        def __init__(self, **kwargs):
            super(Host.Credential, self).__init__(**kwargs)
            self.ipmi = kwargs.get('ipmi')

    def create(self, cancel=False, validate_credentials=False):
        """Creates a host in the UI.

        Args:
           cancel (boolean): Whether to cancel out of the creation. The cancel is done after all the
               information present in the Host has been filled in the UI.
           validate_credentials (boolean): Whether to validate credentials - if True and the
               credentials are invalid, an error will be raised.
        """
        view = navigate_to(self, "Add")
        view.fill({
            "name": self.name,
            "hostname": self.hostname or self.ip_address,
            "host_platform": self.host_platform,
            "custom_ident": self.custom_ident,
            "ipmi_address": self.ipmi_address,
            "mac_address": self.mac_address
        })
        if self.credentials is not None:
            view.default.fill({
                "username": self.credentials.principal,
                "password": self.credentials.secret,
                "confirm_password": self.credentials.verify_secret,
            })
            if validate_credentials:
                view.default.validate_button.click()
        if self.ipmi_credentials is not None:
            view.ipmi.fill({
                "username": self.ipmi_credentials.principal,
                "password": self.ipmi_credentials.secret,
                "confirm_password": self.ipmi_credentials.verify_secret,
            })
            if validate_credentials:
                view.ipmi.validate_button.click()
        if not cancel:
            view.add_button.click()
            flash_message = 'Host / Node " {}" was added'.format(self.name)
        else:
            view.cancel_button.click()
            flash_message = "Add of new Host / Node was cancelled by the user"
        view = self.create_view(InfraHostsAllView)
        assert view.is_displayed
        view.flash.assert_success_message(flash_message)

    def update(self, updates, cancel=False, validate_credentials=False):
        """
        Updates a host in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        credentials = updates.get("credentials")
        ipmi_credentials = updates.get("ipmi_credentials")
        if credentials is not None:
            if view.change_stored_password.is_displayed:
                view.change_stored_password.click()
            credentials_changed = view.default.fill({
                "username": credentials.principal,
                "password": credentials.secret,
                "confirm_password": credentials.verify_secret,
            })
            if validate_credentials:
                view.default.validate_button.click()
        if ipmi_credentials is not None:
            if view.change_stored_password.is_displayed:
                view.change_stored_password.click()
            ipmi_credentials_changed = view.ipmi.fill({
                "username": ipmi_credentials.principal,
                "password": ipmi_credentials.secret,
                "confirm_password": ipmi_credentials.verify_secret,
            })
            if validate_credentials:
                view.ipmi.validate_button.click()
        changed = any([changed, credentials_changed, ipmi_credentials_changed])
        if changed:
            view.save_button.click()
            logger.debug("Trying to save update for host with id: %s", str(self.get_db_id))
            view = self.create_view(InfraHostDetailsView)
            view.flash.assert_success_message(
                'Host / Node "{}" was saved'.format(updates.get("name", self.name)))
        else:
            view.cancel_button.click()
            view.flash.assert_success_message(
                'Edit of Host / Node "{}" was cancelled by the user'.format(
                    updates.get("name", self.name)))

    def delete(self, cancel=True):
        """
        Deletes a host from CFME.

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Remove item", handle_alert=cancel)
        if not cancel:
            view = self.create_view(InfraHostsAllView)
            assert view.is_displayed
            view.flash.assert_success_message("The selected Hosts / Nodes was deleted")

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins."""
        view = navigate_to(self, "Details")
        if refresh:
            view.browser.selenium.refresh()
            view.flush_widget_cache()

    def execute_button(self, button_group, button, cancel=True):
        navigate_to(self, 'Details')
        host_btn = partial(tb.select, button_group)
        host_btn(button, invokes_alert=True)
        sel.click(form_buttons.submit)
        flash.assert_success_message("Order Request was Submitted")
        host_btn(button, invokes_alert=True)
        sel.click(form_buttons.cancel)
        flash.assert_success_message("Service Order was cancelled by the user")

    def power_on(self):
        view = navigate_to(self, "Details")
        view.toolbar.power.item_select("Power On", handle_alert=True)

    def power_off(self):
        view = navigate_to(self, "Details")
        view.toolbar.power.item_select("Power Off", handle_alert=True)

    def get_power_state(self):
        return self.get_detail("Properties", "Power State")

    def refresh(self, cancel=False):
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Refresh Relationships and Power States",
            handle_alert=cancel)

    def wait_for_host_state_change(self, desired_state, timeout=300):
        """Wait for Host to come to desired state.
        This function waits just the needed amount of time thanks to wait_for.
        Args:
            desired_state: 'on' or 'off'
            timeout: Specify amount of time (in seconds) to wait until TimedOutError is raised
        """

        def _looking_for_state_change():
            tb.refresh()
            return 'currentstate-' + desired_state in find_quadicon(self.name,
                                                                    do_not_navigate=False).state

        navigate_and_select_all_hosts(self.name, self.provider)
        return wait_for(_looking_for_state_change, num_sec=timeout)

    def get_ipmi(self):
        return IPMI(
            hostname=self.ipmi_address,
            username=self.ipmi_credentials.principal,
            password=self.ipmi_credentials.secret,
            interface_type=self.interface_type
        )

    def get_detail(self, title, field):
        """ Gets details from the details summary tables

        Args:
            title (str): Summary Table title
            field (str): Summary table field name
        Returns: A string representing the contents of the SummaryTable's value.
        """
        view = navigate_to(self, "Details")
        return getattr(view.summary, title.lower().replace(" ", "_")).read()[field]

    @property
    def exists(self):
        navigate_to(self, 'All')
        for page in paginator.pages():
            if sel.is_displayed(Quadicon(self.name, 'host')):
                return True
        else:
            return False

    @property
    def has_valid_credentials(self):
        """ Check if host has valid credentials saved

        Returns: ``True`` if credentials are saved and valid; ``False`` otherwise
        """
        navigate_to(self, 'All')
        quad = Quadicon(self.name, 'host')
        return 'checkmark' in quad.creds

    def get_datastores(self):
        """ Gets list of all datastores used by this host"""
        navigate_to(self, 'Details')
        list_acc.select('Relationships', 'Datastores', by_title=False, partial=True)
        return [q.name for q in Quadicon.all("datastore")]

    @property
    def get_db_id(self):
        if self.db_id is None:
            self.db_id = self.appliance.host_id(self.name)
            return self.db_id
        else:
            return self.db_id

    def run_smartstate_analysis(self):
        """Runs smartstate analysis on this host.

        Note:
            The host must have valid credentials already set up for this to work.
        """
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Perform SmartState Analysis", handle_alert=True)
        view.flash.assert_success_message('"{}": Analysis successfully initiated'.format(self.name))

    def check_compliance(self, timeout=240):
        """Initiates compliance check and waits for it to finish."""
        view = navigate_to(self, "Details")
        original_state = self.compliance_status
        view.toolbar.policy.item_select("Check Compliance of Last Known Configuration",
            handle_alert=True)
        view.flash.assert_no_errors()
        wait_for(
            lambda: self.compliance_status != original_state,
            num_sec=timeout, delay=5, message="compliance of {} checked".format(self.name)
        )

    @property
    def compliance_status(self):
        """Returns the title of the compliance SummaryTable. The title contains datetime so it can
        be compared.

        Returns:
            :py:class:`NoneType` if no title is present (no compliance checks before), otherwise str
        """
        view = navigate_to(self, "Details")
        view.browser.selenium.refresh()
        return self.get_detail("Compliance", "Status")

    @property
    def is_compliant(self):
        """Check if the Host is compliant.

        Returns:
            :py:class:`bool`
        """
        text = self.compliance_status.strip().lower()
        if text.startswith("non-compliant"):
            return False
        elif text.startswith("compliant"):
            return True
        else:
            raise ValueError("{} is not a known state for compliance".format(text))

    def equal_drift_results(self, row_text, section, *indexes):
        """ Compares drift analysis results of a row specified by it's title text

        Args:
            row_text: Title text of the row to compare
            section: Accordion section where the change happened; this section must be activated
            indexes: Indexes of results to compare starting with 0 for first row (latest result).
                     Compares all available drifts, if left empty (default).

        Note:
            There have to be at least 2 drift results available for this to work.

        Returns:
            ``True`` if equal, ``False`` otherwise.
        """
        # mark by indexes or mark all
        navigate_to(self, 'Details')
        list_acc.select('Relationships',
            version.pick({
                version.LOWEST: 'Show host drift history',
                '5.4': 'Show Host drift history'}))
        if indexes:
            drift_table.select_rows_by_indexes(*indexes)
        else:
            # We can't compare more than 10 drift results at once
            # so when selecting all, we have to limit it to the latest 10
            if len(list(drift_table.rows())) > 10:
                drift_table.select_rows_by_indexes(*range(0, 10))
            else:
                drift_table.select_all()
        tb.select("Select up to 10 timestamps for Drift Analysis")

        # Make sure the section we need is active/open
        sec_loc_map = {
            'Properties': 'Properties',
            'Security': 'Security',
            'Configuration': 'Configuration',
            'My Company Tags': 'Categories'}
        active_sec_loc = "//div[@id='all_sections_treebox']//li[contains(@id, 'group_{}')]"\
            "/span[contains(@class, 'dynatree-selected')]".format(sec_loc_map[section])
        sec_checkbox_loc = "//div[@id='all_sections_treebox']//li[contains(@id, 'group_{}')]"\
            "//span[contains(@class, 'dynatree-checkbox')]".format(sec_loc_map[section])
        sec_apply_btn = "//div[@id='accordion']/a[contains(normalize-space(text()), 'Apply')]"

        # If the section is not active yet, activate it
        if not sel.is_displayed(active_sec_loc):
            sel.click(sec_checkbox_loc)
            sel.click(sec_apply_btn)

        if not tb.is_active("All attributes"):
            tb.select("All attributes")
        d_grid = DriftGrid()
        if any(d_grid.cell_indicates_change(row_text, i) for i in range(0, len(indexes))):
            return False
        return True

    def tag(self, tag, **kwargs):
        """Tags the system by given tag"""
        navigate_to(self, 'Details')
        mixins.add_tag(tag, **kwargs)

    def untag(self, tag):
        """Removes the selected tag off the system"""
        navigate_to(self, 'Details')
        mixins.remove_tag(tag)


@navigator.register(Host)
class All(CFMENavigateStep):
    VIEW = InfraHostsAllView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self):
        try:
            self.prerequisite_view.navigation.select("Compute", "Infrastructure", "Hosts")
        except NoSuchElementException:
            self.prerequisite_view.navigation.select("Compute", "Infrastructure", "Nodes")

    def resetter(self):
        self.view.toolbar.grid_view_button.click()
        self.view.pagination_pane.check_all()
        self.view.pagination_pane.uncheck_all()


@navigator.register(Host)
class Details(CFMENavigateStep):
    VIEW = InfraHostDetailsView
    prerequisite = NavigateToSibling("All")

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))


@navigator.register(Host)
class Edit(CFMENavigateStep):
    VIEW = InfraHostEditView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this item")


@navigator.register(Host)
class Add(CFMENavigateStep):
    VIEW = InfraHostAddView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a New item")


@navigator.register(Host)
class Discover(CFMENavigateStep):
    VIEW = InfraHostDiscoverView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Discover items")


@navigator.register(Host)
class PolicyAssignment(CFMENavigateStep):
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select("Manage Policies")


@navigator.register(Host)
class Provision(CFMENavigateStep):
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.lifecycle.item_select("Provision this item")


@navigator.register(Host)
class Timelines(CFMENavigateStep):
    VIEW = InfraHostTimelinesView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select("Timelines")


def get_credentials_from_config(credential_config_name):
    creds = conf.credentials[credential_config_name]
    return Host.Credential(principal=creds['username'],
                           secret=creds['password'])


def get_from_config(provider_config_name):
    """
    Creates a Host object given a yaml entry in cfme_data.

    Usage:
        get_from_config('esx')

    Returns: A Host object that has methods that operate on CFME
    """
    # TODO: Include provider key in YAML and include provider object when creating
    prov_config = conf.cfme_data.get('management_hosts', {})[provider_config_name]
    credentials = get_credentials_from_config(prov_config['credentials'])
    ipmi_credentials = get_credentials_from_config(prov_config['ipmi_credentials'])
    ipmi_credentials.ipmi = True

    return Host(name=prov_config['name'],
                hostname=prov_config['hostname'],
                ip_address=prov_config['ipaddress'],
                custom_ident=prov_config.get('custom_ident'),
                host_platform=prov_config.get('host_platform'),
                ipmi_address=prov_config['ipmi_address'],
                mac_address=prov_config['mac_address'],
                interface_type=prov_config.get('interface_type', 'lan'),
                credentials=credentials,
                ipmi_credentials=ipmi_credentials)


def wait_for_a_host():
    navigate_to(Host, 'All')
    logger.info('Waiting for a host to appear...')
    wait_for(paginator.rec_total, fail_condition=None, message="Wait for any host to appear",
             num_sec=1000, fail_func=sel.refresh)


def wait_for_host_delete(host):
    navigate_to(Host, 'All')
    quad = Quadicon(host.name, 'host')
    logger.info('Waiting for a host to delete...')
    wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait host to disappear", num_sec=500, fail_func=sel.refresh)


def wait_for_host_to_appear(host):
    navigate_to(Host, 'All')
    quad = Quadicon(host.name, 'host')
    logger.info('Waiting for a host to appear...')
    wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait host to appear", num_sec=1000, fail_func=sel.refresh)


def get_all_hosts(do_not_navigate=False):
    """Returns list of all hosts"""
    if not do_not_navigate:
        navigate_to(Host, 'All')
    return [q.name for q in Quadicon.all("host")]


def find_quadicon(host, do_not_navigate=False):
    """Find and return a quadicon belonging to a specific host

    Args:
        host: Host name as displayed at the quadicon
    Returns: :py:class:`cfme.web_ui.Quadicon` instance
    """
    if not do_not_navigate:
        navigate_to(Host, 'All')
    for page in paginator.pages():
        quadicon = Quadicon(host, "host")
        if sel.is_displayed(quadicon):
            return quadicon
    else:
        raise HostNotFound("Host '{}' not found in UI!".format(host))


def navigate_and_select_all_hosts(host_names, provider=None):
    """ Reduces some redundant code shared between methods """
    if isinstance(host_names, basestring):
        host_names = [host_names]

    if provider:
        navigate_to(provider, 'ProviderNodes')
    else:
        navigate_to(Host, 'All')

    if paginator.page_controls_exist():
        paginator.results_per_page(1000)
        sel.click(paginator.check_all())
    else:
        for host_name in host_names:
            sel.check(Quadicon(host_name, 'host').checkbox())
