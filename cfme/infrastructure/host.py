""" A model of an Infrastructure Host in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var credentials_form: A :py:class:`cfme.web_ui.Form` object describing the credentials form.
"""

from functools import partial

import ui_navigate as nav

import cfme
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
import cfme.web_ui.toolbar as tb
import utils.conf as conf
from cfme.exceptions import HostNotFound
from cfme.web_ui import (
    Region, Quadicon, Form, Select, CheckboxTree, CheckboxTable, DriftGrid, fill, form_buttons,
    paginator, Input
)
from cfme.web_ui.form_buttons import FormButton
from cfme.web_ui import listaccordion as list_acc
from utils.db_queries import get_host_id
from utils.ipmi import IPMI
from utils.log import logger
from utils.update import Updateable
from utils.wait import wait_for
from utils import version
from utils.pretty import Pretty


# Page specific locators
details_page = Region(infoblock_type='detail')

properties_form = Form(
    fields=[
        ('name_text', Input("name")),
        ('hostname_text', Input("hostname")),
        ('ipaddress_text', Input("ipaddress"), {"removed_since": "5.4.0.0.15"}),
        ('custom_ident_text', Input("custom")),
        ('host_platform', Select('//select[@id="user_assigned_os"]')),
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
        ('validate_btn', form_buttons.validate)
    ])

manage_policies_tree = CheckboxTree(
    {
        version.LOWEST: "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='protect_treebox']/ul"
    }
)

drift_table = CheckboxTable({
    version.LOWEST: "//table[@class='style3']",
    "5.4": "//th[normalize-space(.)='Timestamp']/ancestor::table[1]"
})

host_add_btn = FormButton('Add this Host')
forced_saved = FormButton("Save Changes", dimmed_alt="Save", force_click=True)
cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')
pow_btn = partial(tb.select, 'Power')
lif_btn = partial(tb.select, 'Lifecycle')

nav.add_branch('infrastructure_hosts',
               {'infrastructure_host_new': lambda _: cfg_btn(
                   version.pick({version.LOWEST: 'Add a New Host',
                                 '5.4': 'Add a New item'})),
                'infrastructure_host_discover': lambda _: cfg_btn(
                    'Discover Hosts'),
                'infrastructure_host': [lambda ctx: sel.click(Quadicon(ctx['host'].name,
                                                                      'host')),
                                   {'infrastructure_host_edit':
                                    lambda _: cfg_btn('Edit this Host'),
                                    'infrastructure_host_policy_assignment':
                                    lambda _: pol_btn('Manage Policies'),
                                    'infrastructure_provision_host':
                                    lambda _: lif_btn(
                                        version.pick({version.LOWEST: 'Provision this Host',
                                                      '5.4': 'Provision items'}))}]})


class Host(Updateable, Pretty):
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
        credentials (Credential): see Credential inner class.
        ipmi_credentials (Credential): see Credential inner class.

    Usage:

        myhost = Host(name='vmware',
                      credentials=Provider.Credential(principal='admin', secret='foobar'))
        myhost.create()

    """
    pretty_attrs = ['name', 'hostname', 'ip_address', 'custom_ident']

    def __init__(self, name=None, hostname=None, ip_address=None, custom_ident=None,
                 host_platform=None, ipmi_address=None, mac_address=None, credentials=None,
                 ipmi_credentials=None, interface_type='lan'):
        self.name = name
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

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'hostname_text': kwargs.get('hostname'),
                'ipaddress_text': kwargs.get('ip_address'),
                'custom_ident_text': kwargs.get('custom_ident'),
                'host_platform': kwargs.get('host_platform'),
                'ipmi_address_text': kwargs.get('ipmi_address'),
                'mac_address_text': kwargs.get('mac_address')}

    class Credential(cfme.Credential, Updateable):
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
        sel.force_navigate('infrastructure_host_new')
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

        sel.force_navigate('infrastructure_host_edit', context={'host': self})
        fill(properties_form, self._form_mapping(**updates))
        fill(credential_form, updates.get('credentials', None), validate=validate_credentials)

        # Workaround for issue with form_button staying dimmed.
        try:
            logger.debug("Trying to save update for host with id: " + str(self.get_db_id))
            self._submit(cancel, forced_saved)
            logger.debug("save worked, no exception")
        except Exception as e:
            logger.debug("exception detected: " + str(e))
            sel.browser().execute_script(
                "$j.ajax({type: 'POST', url: '/host/form_field_changed/%s',"
                " data: {'default_userid':'%s'}})" %
                (str(sel.current_url().split('/')[5]), updates.get('credentials', None).principal))
            sel.browser().execute_script(
                "$j.ajax({type: 'POST', url: '/host/form_field_changed/%s',"
                " data: {'default_password':'%s'}})" %
                (str(sel.current_url().split('/')[5]), updates.get('credentials', None).secret))
            sel.browser().execute_script(
                "$j.ajax({type: 'POST', url: '/host/form_field_changed/%s',"
                " data: {'default_verify':'%s'}})" %
                (str(sel.current_url().split('/')[5]),
                    updates.get('credentials', None).verify_secret))
            self._submit(cancel, forced_saved)

    def delete(self, cancel=True):
        """
        Deletes a host from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('infrastructure_host', context={'host': self})
        cfg_btn('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def execute_button(self, button_group, button, cancel=True):
        sel.force_navigate('infrastructure_host', context={'host': self})
        host_btn = partial(tb.select, button_group)
        host_btn(button, invokes_alert=True)
        sel.click(form_buttons.submit)
        flash.assert_success_message("Order Request was Submitted")
        host_btn(button, invokes_alert=True)
        sel.click(form_buttons.cancel)
        flash.assert_success_message("Service Order was cancelled by the user")

    def power_on(self):
        sel.force_navigate('infrastructure_host', context={'host': self})
        pow_btn('Power On')
        sel.handle_alert()

    def power_off(self):
        sel.force_navigate('infrastructure_host', context={'host': self})
        pow_btn('Power Off')
        sel.handle_alert()

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
        if not self._on_detail_page():
            sel.force_navigate('infrastructure_host', context={'host': self})
        return details_page.infoblock.text(*ident)

    def _on_detail_page(self):
        """ Returns ``True`` if on the hosts detail page, ``False`` if not."""
        return sel.is_displayed('//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s")]'
                                % self.name)

    @property
    def exists(self):
        sel.force_navigate('infrastructure_hosts')
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
        sel.force_navigate('infrastructure_hosts')
        quad = Quadicon(self.name, 'host')
        return quad.creds == 'checkmark'

    def _assign_unassign_policy_profiles(self, assign, *policy_profile_names):
        """DRY function for managing policy profiles.

        See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

        Args:
            assign: Wheter to assign or unassign.
            policy_profile_names: :py:class:`str` with Policy Profile names.
        """
        sel.force_navigate('infrastructure_host_policy_assignment', context={'host': self})
        for policy_profile in policy_profile_names:
            if assign:
                manage_policies_tree.check_node(policy_profile)
            else:
                manage_policies_tree.uncheck_node(policy_profile)
        sel.click(form_buttons.save)

    def assign_policy_profiles(self, *policy_profile_names):
        """ Assign Policy Profiles to this Host.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        self._assign_unassign_policy_profiles(True, *policy_profile_names)

    def unassign_policy_profiles(self, *policy_profile_names):
        """ Unssign Policy Profiles to this Host.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        self._assign_unassign_policy_profiles(False, *policy_profile_names)

    def get_datastores(self):
        """ Gets list of all datastores used by this host"""
        sel.force_navigate('infrastructure_host', context={'host': self})
        list_acc.select('Relationships', version.pick({version.LOWEST: 'Show Datastores',
                                                       '5.3': 'Show all Datastores'}))

        datastores = set([])
        for page in paginator.pages():
            for title in sel.elements(
                    "//div[@id='quadicon']/../../../tr/td/a[contains(@href,'storage/show')]"):
                datastores.add(sel.get_attribute(title, "title"))
        return datastores

    @property
    def get_db_id(self):
        if self.db_id is None:
            self.db_id = get_host_id(self.name)
            return self.db_id
        else:
            return self.db_id

    def run_smartstate_analysis(self):
        """ Runs smartstate analysis on this host

        Note:
            The host must have valid credentials already set up for this to work.
        """
        sel.force_navigate('infrastructure_host', context={'host': self})
        tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_contain('"{}": Analysis successfully initiated'.format(self.name))

    def equal_drift_results(self, row_text, *indexes):
        """ Compares drift analysis results of a row specified by it's title text

        Args:
            row_text: Title text of the row to compare
            indexes: Indexes of results to compare starting with 0 for first row (latest result).
                     Compares all available drifts, if left empty (default).

        Note:
            There have to be at least 2 drift results available for this to work.

        Returns:
            ``True`` if equal, ``False`` otherwise.
        """
        # mark by indexes or mark all
        sel.force_navigate('infrastructure_host', context={'host': self})
        list_acc.select('Relationships', 'Show host drift history')
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

        d_grid = DriftGrid()
        if not tb.is_active("All attributes"):
            tb.select("All attributes")
        if any(d_grid.cell_indicates_change(row_text, i) for i in range(0, len(indexes))):
            return False
        return True


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
    sel.force_navigate('infrastructure_hosts')
    logger.info('Waiting for a host to appear...')
    wait_for(paginator.rec_total, fail_condition=None, message="Wait for any host to appear",
             num_sec=1000, fail_func=sel.refresh)


def wait_for_host_delete(host):
    sel.force_navigate('infrastructure_hosts')
    quad = Quadicon(host.name, 'host')
    logger.info('Waiting for a host to delete...')
    wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait host to disappear", num_sec=500, fail_func=sel.refresh)


def wait_for_host_to_appear(host):
    sel.force_navigate('infrastructure_hosts')
    quad = Quadicon(host.name, 'host')
    logger.info('Waiting for a host to appear...')
    wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait host to appear", num_sec=1000, fail_func=sel.refresh)


def get_all_hosts(do_not_navigate=False):
    """Returns list of all hosts"""
    if not do_not_navigate:
        sel.force_navigate('infrastructure_hosts')
    hosts = set([])
    for page in paginator.pages():
        for title in sel.elements(
                "//div[@id='quadicon']/../../../tr/td/a[contains(@href,'host/show')]"):
            hosts.add(sel.get_attribute(title, "title"))
    return hosts


def find_quadicon(host, do_not_navigate=False):
    """Find and return a quadicon belonging to a specific host

    Args:
        host: Host name as displayed at the quadicon
    Returns: :py:class:`cfme.web_ui.Quadicon` instance
    """
    if not do_not_navigate:
        sel.force_navigate('infrastructure_hosts')
    for page in paginator.pages():
        quadicon = Quadicon(host, "host")
        if sel.is_displayed(quadicon):
            return quadicon
    else:
        raise HostNotFound("Host '{}' not found in UI!".format(host))
