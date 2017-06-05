""" A model of an Infrastructure Host in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var credentials_form: A :py:class:`cfme.web_ui.Form` object describing the credentials form.
"""

from functools import partial
from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException

from cfme.base.login import BaseLoggedInPage
from cfme.base.credential import Credential as BaseCredential
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
import cfme.web_ui.toolbar as tb
from utils import conf
from cfme.exceptions import HostNotFound
from cfme.web_ui import (
    AngularSelect, Region, Quadicon, Form, Select, CheckboxTree, CheckboxTable, DriftGrid, fill,
    form_buttons, paginator, Input, mixins, match_location
)
from cfme.web_ui.form_buttons import FormButton, change_stored_password
from cfme.web_ui import listaccordion as list_acc
from utils.ipmi import IPMI
from utils.log import logger
from utils.update import Updateable
from utils.wait import wait_for
from utils import deferred_verpick, version
from utils.pretty import Pretty
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.appliance import Navigatable
from widgetastic_manageiq import TimelinesView

from cfme.common import PolicyProfileAssignable

# Page specific locators
details_page = Region(infoblock_type='detail')

page_title_loc = '//div[@id="center_div" or @id="main-content"]//h1'

properties_form = Form(
    fields=[
        ('name_text', Input("name")),
        ('hostname_text', Input("hostname")),
        ('ipaddress_text', Input("ipaddress"), {"removed_since": "5.4.0.0.15"}),
        ('custom_ident_text', Input("custom")),
        ('host_platform', {
            version.LOWEST: Select('//select[@id="user_assigned_os"]'),
            '5.5': AngularSelect('user_assigned_os')}),
        ('ipmi_address_text', Input("ipmi_address")),
        ('mac_address_text', Input("mac_address")),
    ])

credential_form = Form(
    fields=[
        ('default_button', "//div[@id='auth_tabs']/ul/li/a[@href='#default']"),
        ('default_principal', Input("default_userid")),
        ('default_secret', Input("default_password")),
        ('default_verify_secret', Input("default_verify")),
        ('ipmi_button', "//div[@id='auth_tabs']/ul/li/a[@href='#ipmi']"),
        ('ipmi_principal', Input("ipmi_userid")),
        ('ipmi_secret', Input("ipmi_password")),
        ('ipmi_verify_secret', Input("ipmi_verify")),
        ('validate_btn', form_buttons.validate),
        ('validate_multi_host', form_buttons.validate_multi_host),
        ('save_btn', {version.LOWEST: form_buttons.save,
            '5.5': form_buttons.angular_save}),
        ('cancel_changes', {version.LOWEST: form_buttons.cancel_changes,
            '5.5': form_buttons.cancel}),
        ('validate_host', {version.LOWEST: Select('select#validate_id'),
            '5.5': AngularSelect('validate_id')}),
    ])

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
cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')
pow_btn = partial(tb.select, 'Power')
lif_btn = partial(tb.select, 'Lifecycle')
mon_btn = partial(tb.select, 'Monitoring')


match_page = partial(match_location, controller='host',
                     title='Hosts')


class InfraHostTimelinesView(TimelinesView, BaseLoggedInPage):

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', '/host'] and \
            super(TimelinesView, self).is_displayed


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

    forced_saved = deferred_verpick(
        {version.LOWEST: form_buttons.FormButton(
            "Save changes", dimmed_alt="Save changes", force_click=True),
         '5.8': form_buttons.FormButton(
            "Save", dimmed_alt="Save", force_click=True)})

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

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'hostname_text': kwargs.get('hostname'),
                'ipaddress_text': kwargs.get('ip_address'),
                'custom_ident_text': kwargs.get('custom_ident'),
                'host_platform': kwargs.get('host_platform'),
                'ipmi_address_text': kwargs.get('ipmi_address'),
                'mac_address_text': kwargs.get('mac_address')}

    class Credential(BaseCredential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using IPMI type credential, ipmi = True"""

        def __init__(self, **kwargs):
            super(Host.Credential, self).__init__(**kwargs)
            self.ipmi = kwargs.get('ipmi')

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(form_buttons.cancel)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False, validate_credentials=False):
        """
        Creates a host in the UI

        Args:
           cancel (boolean): Whether to cancel out of the creation.  The cancel is done
               after all the information present in the Host has been filled in the UI.
           validate_credentials (boolean): Whether to validate credentials - if True and the
               credentials are invalid, an error will be raised.
        """
        navigate_to(self, 'Add')
        fill(properties_form, self._form_mapping(True, **self.__dict__))
        fill(credential_form, self.credentials, validate=validate_credentials)
        fill(credential_form, self.ipmi_credentials, validate=validate_credentials)
        self._submit(cancel, host_add_btn)

    def update(self, updates, cancel=False, validate_credentials=False):
        """
        Updates a host in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        navigate_to(self, 'Edit')
        change_stored_password()
        fill(credential_form, updates.get('credentials', None), validate=validate_credentials)

        logger.debug("Trying to save update for host with id: " + str(self.get_db_id))
        self._submit(cancel, self.forced_saved)

    def delete(self, cancel=True):
        """
        Deletes a host from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        navigate_to(self, 'Details')
        if self.appliance.version >= '5.7':
            btn_name = "Remove item"
        else:
            btn_name = "Remove from the VMDB"
        cfg_btn(btn_name, invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins."""
        navigate_to(self, 'Details')
        if refresh:
            sel.refresh()

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
        navigate_to(self, 'Details')
        pow_btn('Power On', invokes_alert=True)
        sel.handle_alert()

    def power_off(self):
        navigate_to(self, 'Details')
        pow_btn('Power Off', invokes_alert=True)
        sel.handle_alert()

    def get_power_state(self):
        return self.get_detail('Properties', 'Power State')
        # return str(find_quadicon(self.name, do_not_navigate=True).state)
        # return state.split()[1]

    def refresh(self, cancel=False):
        tb.select("Configuration", "Refresh Relationships and Power States", invokes_alert=True)
        sel.handle_alert(cancel=cancel)

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
        return IPMI(hostname=self.ipmi_address, username=self.ipmi_credentials.principal,
                    password=self.ipmi_credentials.secret, interface_type=self.interface_type)

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific host.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        navigate_to(self, 'Details')
        return details_page.infoblock.text(*ident)

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
        """ Runs smartstate analysis on this host

        Note:
            The host must have valid credentials already set up for this to work.
        """
        navigate_to(self, 'Details')
        tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_contain('"{}": Analysis successfully initiated'.format(self.name))

    def check_compliance(self, timeout=240):
        """Initiates compliance check and waits for it to finish."""
        navigate_to(self, 'Details')
        original_state = self.compliance_status
        tb.select('Policy', 'Check Compliance of Last Known Configuration', invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()
        wait_for(
            lambda: self.compliance_status != original_state,
            num_sec=timeout, delay=5, message="compliance of {} checked".format(self.name)
        )

    @property
    def compliance_status(self):
        """Returns the title of the compliance infoblock. The title contains datetime so it can be
        compared.

        Returns:
            :py:class:`NoneType` if no title is present (no compliance checks before), otherwise str
        """
        sel.refresh()
        return self.get_detail('Compliance', 'Status')

    @property
    def is_compliant(self):
        """Check if the Host is compliant

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


@navigator.register(Host, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        try:
            self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Hosts')
        except NoSuchElementException:
            self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Nodes')

    def resetter(self):
        tb.select("Grid View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Host, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def am_i_here(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))


@navigator.register(Host, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this item')


@navigator.register(Host, 'Add')
class Add(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Add a New item')


@navigator.register(Host, 'Discover')
class Discover(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Discover items')


@navigator.register(Host, 'PolicyAssignment')
class PolicyAssignment(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Manage Policies')


@navigator.register(Host, 'Provision')
class Provision(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        lif_btn('Provision this item')


@navigator.register(Host, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = InfraHostTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon_btn('Timelines')


@fill.method((Form, Host.Credential))
def _fill_credential(form, cred, validate=None):
    """How to fill in a credential (either ipmi or default).  Validates the
    credential if that option is passed in.
    """
    if cred.ipmi:
        fill(credential_form, {'ipmi_button': True,
                               'ipmi_principal': cred.principal,
                               'ipmi_secret': cred.secret,
                               'ipmi_verify_secret': cred.verify_secret,
                               'validate_btn': validate})
    else:
        fill(credential_form, {'default_principal': cred.principal,
                               'default_secret': cred.secret,
                               'default_verify_secret': cred.verify_secret,
                               'validate_btn': validate})
    if validate:
        flash.assert_no_errors()


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
                custom_ident=prov_config.get('custom_ident', None),
                host_platform=prov_config.get('host_platform', None),
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
