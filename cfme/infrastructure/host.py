# -*- coding: utf-8 -*-
"""A model of an Infrastructure Host in CFME."""
import attr

from manageiq_client.api import APIException
from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException
from widgetastic.utils import VersionPick

from cfme.base.credential import Credential as BaseCredential
from cfme.common import PolicyProfileAssignable, Taggable
from cfme.common.candu_views import HostInfraUtilizationView
from cfme.common.host_views import (
    HostAddView,
    HostDetailsView,
    HostDiscoverView,
    HostDriftAnalysis,
    HostDriftHistory,
    HostEditView,
    HostsView,
    HostTimelinesView
)
from cfme.exceptions import ItemNotFound
from cfme.infrastructure.datastore import HostAllDatastoresView
from cfme.modeling.base import BaseEntity, BaseCollection

from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigate_to, navigator
from cfme.utils.ipmi import IPMI
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for


@attr.s
class Host(BaseEntity, Updateable, Pretty, PolicyProfileAssignable, Taggable):
    """Model of an infrastructure host in cfme.

    Args:
        name: Name of the host.
        hostname: Hostname of the host.
        ip_address: The IP address as a string.
        custom_ident: The custom identifiter.
        host_platform: Included but appears unused in CFME at the moment.
        ipmi_address: The IPMI address.
        mac_address: The mac address of the system.
        credentials Combines three types of credentials - 'default', 'remote_login',
                    'web_services', all three can be passed.
                    Each contains (:py:class:`Credential`): see Credential inner class.
        ipmi_credentials (:py:class:`Credential`): see Credential inner class.

    Usage:

        myhost = Host(name='vmware',
                      credentials={
                                'default': Provider.Credential(principal='admin', secret='foobar')})
        myhost.create()

    """
    pretty_attrs = ['name', 'hostname', 'ip_address', 'custom_ident']

    name = attr.ib()
    provider = attr.ib(default=None)
    hostname = attr.ib(default=None)
    ip_address = attr.ib(default=None)
    custom_ident = attr.ib(default=None)
    host_platform = attr.ib(default=None)
    ipmi_address = attr.ib(default=None)
    mac_address = attr.ib(default=None)
    credentials = attr.ib(default=attr.Factory(dict))
    ipmi_credentials = attr.ib(default=None)
    interface_type = attr.ib(default='lan')
    db_id = None

    class Credential(BaseCredential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using IPMI type credential, ipmi = True"""

        def __init__(self, **kwargs):
            super(Host.Credential, self).__init__(**kwargs)
            self.ipmi = kwargs.get('ipmi')

    def update(self, updates, validate_credentials=False):
        """Updates a host in the UI. Better to use utils.update.update context manager than call
        this directly.

        Args:
           updates (dict): fields that are changing.
        """

        view = navigate_to(self, "Edit")
        changed = view.fill({
            "name": updates.get("name"),
            "hostname": updates.get("hostname") or updates.get("ip_address"),
            "custom_ident": updates.get("custom_ident"),
            "ipmi_address": updates.get("ipmi_address"),
            "mac_address": updates.get("mac_address")
        })
        credentials = updates.get("credentials")
        ipmi_credentials = updates.get("ipmi_credentials")
        credentials_changed = False
        ipmi_credentials_changed = False
        if credentials is not None:
            for creds_type in credentials:
                cred_endpoint = getattr(view.endpoints, creds_type)
                if cred_endpoint.change_stored_password.is_displayed:
                    cred_endpoint.change_stored_password.click()
                credentials_changed = cred_endpoint.fill_with(credentials[
                    creds_type].view_value_mapping)
                if validate_credentials:
                    cred_endpoint.validate_button.click()
        if ipmi_credentials is not None:
            if view.endpoints.ipmi.change_stored_password.is_displayed:
                view.endpoints.ipmi.change_stored_password.click()
            ipmi_credentials_changed = view.endpoints.ipmi.fill(ipmi_credentials.view_value_mapping)
            if validate_credentials:
                view.endpoints.ipmi.validate_button.click()
        view.flash.assert_no_error()
        changed = any([changed, credentials_changed, ipmi_credentials_changed])
        if changed:
            view.save_button.click()
            logger.debug("Trying to save update for host with id: %s", str(self.get_db_id))
            view = self.create_view(HostDetailsView)
            view.flash.assert_success_message(
                'Host / Node "{}" was saved'.format(updates.get("name", self.name)))
        else:
            view.cancel_button.click()
            view.flash.assert_success_message(
                'Edit of Host / Node "{}" was cancelled by the user'.format(
                    updates.get("name", self.name)))

    def delete(self, cancel=True):
        """Deletes this host from CFME.

        Args:
            cancel (bool): Whether to cancel the deletion, defaults to True
        """
        view = navigate_to(self, "Details")
        remove_item = VersionPick({
            '5.8': 'Remove item',
            '5.9': 'Remove item from Inventory'})
        view.toolbar.configuration.item_select(remove_item, handle_alert=not cancel)
        if not cancel:
            view = self.create_view(HostsView)
            assert view.is_displayed
            view.flash.assert_success_message("The selected Hosts / Nodes was deleted")

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins.

        Args:
            refresh (bool): Whether to perform the page refresh, defaults to False
        """
        view = navigate_to(self, "Details")
        if refresh:
            view.browser.refresh()
            view.flush_widget_cache()

    def execute_button(self, button_group, button, handle_alert=False):
        view = navigate_to(self, "Details")
        view.toolbar.custom_button(button_group).item_select(button, handle_alert=handle_alert)

    def power_on(self):
        view = navigate_to(self, "Details")
        view.toolbar.power.item_select("Power On", handle_alert=True)

    def power_off(self):
        view = navigate_to(self, "Details")
        view.toolbar.power.item_select("Power Off", handle_alert=True)

    def get_power_state(self):
        view = navigate_to(self, "Details")
        return view.entities.summary("Properties").get_text_of("Power State")

    def refresh(self, cancel=False):
        """Perform 'Refresh Relationships and Power States' for the host.

        Args:
            cancel (bool): Whether the action should be cancelled, default to False
        """
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Refresh Relationships and Power States",
            handle_alert=cancel)

    def wait_for_host_state_change(self, desired_state, timeout=300):
        """Wait for Host to come to desired state. This function waits just the needed amount of
        time thanks to wait_for.

        Args:
            desired_state (str): 'on' or 'off'
            timeout (int): Specify amount of time (in seconds) to wait until TimedOutError is raised
        """
        view = navigate_to(self.parent, "All")

        def _looking_for_state_change():
            entity = view.entities.get_entity(name=self.name)
            return "currentstate-{}".format(desired_state) in entity.data['state']

        return wait_for(
            _looking_for_state_change,
            fail_func=view.browser.refresh,
            num_sec=timeout
        )

    def get_ipmi(self):
        return IPMI(
            hostname=self.ipmi_address,
            username=self.ipmi_credentials.principal,
            password=self.ipmi_credentials.secret,
            interface_type=self.interface_type
        )

    @property
    def exists(self):
        """Checks if the host exists in the UI.

        Returns: :py:class:`bool`
        """
        view = navigate_to(self.parent, "All")
        try:
            view.entities.get_entity(name=self.name, surf_pages=True)
        except ItemNotFound:
            return False
        else:
            return True

    @property
    def has_valid_credentials(self):
        """Checks if host has valid credentials save.

        Returns: :py:class:`bool`
        """
        view = navigate_to(self.parent, "All")
        entity = view.entities.get_entity(name=self.name, surf_pages=True)
        try:
            return entity.data['creds'].strip().lower() == "checkmark"
        except KeyError:
            return False

    def update_credentials_rest(self, credentials):
        """ Updates host's credentials via rest api

        Args:
            credentials (dict) : credentials from yaml file
        Returns: ``True`` if credentials are saved and valid; ``False`` otherwise
        """
        # TODO: Move to Sentaku
        try:
            host = self.appliance.rest_api.collections.hosts.get(name=self.name)
            host.action.edit(credentials={"userid": credentials.principal,
                                          "password": credentials.secret})
        except APIException:
            return False

    def get_datastores(self):
        """Gets list of all datastores used by this host.

        Returns: :py:class:`list` of datastores names
        """
        host_details_view = navigate_to(self, "Details")
        host_details_view.entities.summary("Relationships").click_at("Datastores")
        datastores_view = self.create_view(HostAllDatastoresView)
        assert datastores_view.is_displayed
        return [entity.name for entity in datastores_view.entites.get_all_()]

    @property
    def get_db_id(self):
        if self.db_id is None:
            self.db_id = self.appliance.host_id(self.name)
            return self.db_id
        else:
            return self.db_id

    def run_smartstate_analysis(self, wait_for_task_result=False):
        """Runs smartstate analysis on this host.

        Note:
            The host must have valid credentials already set up for this to work.
        """
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Perform SmartState Analysis", handle_alert=True)
        view.flash.assert_success_message('"{}": Analysis successfully initiated'.format(self.name))
        if wait_for_task_result:
            task = self.appliance.collections.tasks.instantiate(
                name="SmartState Analysis for '{}'".format(self.name), tab='MyOtherTasks')
            task.wait_for_finished()
            return task

    def check_compliance(self, timeout=240):
        """Initiates compliance check and waits for it to finish."""
        view = navigate_to(self, "Details")
        original_state = self.compliance_status
        view.toolbar.policy.item_select("Check Compliance of Last Known Configuration",
            handle_alert=True)
        view.flash.assert_no_error()
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
        view.browser.refresh()
        return view.entities.summary("Compliance").get_text_of("Status")

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

    def equal_drift_results(self, drift_section, section, *indexes):
        """Compares drift analysis results of a row specified by it's title text.

        Args:
            drift_section (str): Title text of the row to compare
            section (str): Accordion section where the change happened
            indexes: Indexes of results to compare starting with 0 for first row (latest result).
                     Compares all available drifts, if left empty (default)

        Note:
            There have to be at least 2 drift results available for this to work.

        Returns:
            :py:class:`bool`
        """

        def _select_rows(indexes):
            for i in indexes:
                drift_history_view.history_table[i][0].click()

        # mark by indexes or mark all
        details_view = navigate_to(self, "Details")
        details_view.entities.summary("Relationships").click_at("Drift History")
        drift_history_view = self.create_view(HostDriftHistory)
        assert drift_history_view.is_displayed
        if indexes:
            _select_rows(indexes)
        else:
            # We can't compare more than 10 drift results at once
            # so when selecting all, we have to limit it to the latest 10
            rows_number = len(list(drift_history_view.history_table.rows()))
            if rows_number > 10:
                _select_rows(range(10))
            else:
                _select_rows(range(rows_number))
        drift_history_view.analyze_button.click()
        drift_analysis_view = self.create_view(HostDriftAnalysis)
        assert drift_analysis_view.is_displayed
        drift_analysis_view.drift_sections.check_node(section)
        drift_analysis_view.apply_button.click()
        if not drift_analysis_view.toolbar.all_attributes.active:
            drift_analysis_view.toolbar.all_attributes.click()
        return drift_analysis_view.drift_analysis.is_changed(drift_section)

    def wait_to_appear(self):
        """Waits for the host to appear in the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for the host to appear...")
        wait_for(
            lambda: self.exists,
            message="Wait for the host to appear",
            num_sec=1000,
            fail_func=view.browser.refresh
        )

    def wait_for_delete(self):
        """Waits for the host to remove from the UI."""
        view = navigate_to(self.parent, "All")
        logger.info("Waiting for a host to delete...")
        wait_for(
            lambda: not self.exists,
            message="Wait for the host to disappear",
            num_sec=500,
            fail_func=view.browser.refresh
        )

    def wait_candu_data_available(self, timeout=900):
        """Waits until C&U data are available for this Host

        Args:
            timeout: Timeout passed to :py:func:`utils.wait.wait_for`
        """
        view = navigate_to(self, 'Details')
        wait_for(
            lambda: view.toolbar.monitoring.item_enabled("Utilization"),
            delay=10, handle_exception=True, num_sec=timeout,
            fail_func=view.browser.refresh
        )


@attr.s
class HostCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.infrastructure.host.Host`."""

    ENTITY = Host

    def check_hosts(self, hosts):
        hosts = list(hosts)
        checked_hosts = list()
        view = navigate_to(self, 'All')

        for host in hosts:
            try:
                view.entities.get_entity(name=host.name, surf_pages=True).check()
                checked_hosts.append(host)
            except ItemNotFound:
                raise ItemNotFound('Could not find host {} in the UI'.format(host.name))
        return view

    def create(self, name, provider=None, credentials=None, hostname=None, ip_address=None,
               host_platform=None, custom_ident=None, ipmi_address=None, mac_address=None,
               ipmi_credentials=None, cancel=False, validate_credentials=False,
               interface_type='lan'):
        """Creates a host in the UI.

        Args:
           cancel (bool): Whether to cancel out of the creation. The cancel is done after all the
               information present in the Host has been filled in the UI.
           validate_credentials (bool): Whether to validate credentials - if True and the
               credentials are invalid, an error will be raised.
        """
        view = navigate_to(self, "Add")
        view.fill({
            "name": name,
            "hostname": hostname or ip_address,
            "host_platform": host_platform,
            "custom_ident": custom_ident,
            "ipmi_address": ipmi_address,
            "mac_address": mac_address
        })
        if credentials is not None:
            for credentials_type in credentials:
                cred_endpoint = getattr(view.endpoints, credentials_type)
                cred_endpoint.fill(credentials.view_value_mapping)
                if validate_credentials:
                    cred_endpoint.validate_button.click()
        if ipmi_credentials is not None:
            view.endpoints.ipmi.fill(ipmi_credentials.view_value_mapping)
            if validate_credentials:
                view.endpoints.ipmi.validate_button.click()
        if not cancel:
            view.add_button.click()
            flash_message = 'Host / Node " {}" was added'.format(name)
        else:
            view.cancel_button.click()
            flash_message = "Add of new Host / Node was cancelled by the user"
        host = self.instantiate(name=name, hostname=hostname, ip_address=ip_address,
                                custom_ident=custom_ident, host_platform=host_platform,
                                ipmi_address=ipmi_address, mac_address=mac_address,
                                credentials=credentials, ipmi_credentials=ipmi_credentials,
                                provider=provider)
        view = host.create_view(HostsView)
        assert view.is_displayed
        view.flash.assert_success_message(flash_message)
        return host

    def all(self, provider):
        """returning all hosts objects"""
        view = navigate_to(self, 'All')
        hosts = [self.instantiate(name=item, provider=provider)
                 for item in view.entities.entity_names]
        return hosts

    def run_smartstate_analysis(self, *hosts):
        view = self.check_hosts(hosts)
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        for host in hosts:
            view.flash.assert_success_message(
                '"{}": Analysis successfully initiated'.format(host.name))

    def delete(self, *hosts):
        """Deletes this host from CFME."""
        view = self.check_hosts(hosts)
        remove_item = VersionPick({
            '5.8': 'Remove items',
            '5.9': 'Remove items from Inventory'})
        view.toolbar.configuration.item_select(remove_item, handle_alert=True)
        view.flash.assert_success_message(
            'Delete initiated for {} Hosts / Nodes from the {} Database'.format(
                len(hosts), self.appliance.product_name))
        for host in hosts:
            host.wait_for_delete()

    def discover(self, from_address, to_address, esx=False, ipmi=False, cancel=False):
        """Discovers hosts."""
        view = navigate_to(self, 'Discover')

        parts = from_address.split('.')
        fill_dict = {
            'esx': esx or None,
            'ipmi': ipmi or None,
            'from_ip1': parts[0],
            'from_ip2': parts[1],
            'from_ip3': parts[2],
            'from_ip4': parts[3],
            'to_ip4': to_address.split('.')[-1]
        }
        view.fill(fill_dict)

        if not cancel:
            view.start_button.click()
            flash_message = 'Hosts / Nodes: Discovery successfully initiated'
        else:
            view.cancel_button.click()
            flash_message = 'Hosts / Nodes Discovery was cancelled by the user'
        view = self.create_view(HostsView)
        assert view.is_displayed
        view.flash.assert_success_message(flash_message)

    def power_on(self, *hosts):
        view = self.check_hosts(hosts)
        view.toolbar.power.item_select("Power On", handle_alert=True)

    def power_off(self, *hosts):
        view = self.check_hosts(hosts)
        view.toolbar.power.item_select("Power Off", handle_alert=True)

    def _get_config(self, host_key):
        host_config = conf.cfme_data.get('management_hosts', {})[host_key]
        credentials = {'default': get_credentials_from_config(host_config['credentials'])}
        ipmi_credentials = get_credentials_from_config(host_config['ipmi_credentials'])
        ipmi_credentials.ipmi = True
        return host_config, credentials, ipmi_credentials

    def get_from_config(self, host_key):
        """Creates a Host object given a yaml entry in cfme_data.

        Usage:
            get_from_config('esx')

        Returns: A Host object that has methods that operate on CFME
        """
        # TODO: Include provider key in YAML and include provider object when creating
        host_config, credentials, ipmi_credentials = self._get_config(host_key)
        return self.instantiate(
            name=host_config['name'],
            hostname=host_config['hostname'],
            ip_address=host_config['ipaddress'],
            custom_ident=host_config.get('custom_ident'),
            host_platform=host_config.get('host_platform'),
            ipmi_address=host_config['ipmi_address'],
            mac_address=host_config['mac_address'],
            interface_type=host_config.get('interface_type', 'lan'),
            credentials={'default': credentials},
            ipmi_credentials=ipmi_credentials
        )

    def create_from_config(self, host_key):
        """Creates a Host object given a yaml entry in cfme_data.

        Usage:
            create_from_config('esx')

        Returns: A Host object that has methods that operate on CFME
        """
        # TODO: Include provider key in YAML and include provider object when creating
        host_config, credentials, ipmi_credentials = self._get_config(host_key)
        return self.create(
            name=host_config['name'],
            hostname=host_config['hostname'],
            ip_address=host_config['ipaddress'],
            custom_ident=host_config.get('custom_ident'),
            host_platform=host_config.get('host_platform'),
            ipmi_address=host_config['ipmi_address'],
            mac_address=host_config['mac_address'],
            interface_type=host_config.get('interface_type', 'lan'),
            credentials={'default': credentials},
            ipmi_credentials=ipmi_credentials
        )


@navigator.register(HostCollection)
class All(CFMENavigateStep):
    VIEW = HostsView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self):
        try:
            self.prerequisite_view.navigation.select("Compute", "Infrastructure", "Hosts")
        except NoSuchElementException:
            self.prerequisite_view.navigation.select("Compute", "Infrastructure", "Nodes")


@navigator.register(Host)
class Details(CFMENavigateStep):
    VIEW = HostDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(Host)
class Edit(CFMENavigateStep):
    VIEW = HostEditView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this item")


@navigator.register(HostCollection)
class Add(CFMENavigateStep):
    VIEW = HostAddView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a New item")


@navigator.register(HostCollection)
class Discover(CFMENavigateStep):
    VIEW = HostDiscoverView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Discover items")


@navigator.register(Host)
class Provision(CFMENavigateStep):
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.lifecycle.item_select("Provision this item")


@navigator.register(Host)
class Timelines(CFMENavigateStep):
    VIEW = HostTimelinesView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select("Timelines")


@navigator.register(Host, "candu")
class Utilization(CFMENavigateStep):
    VIEW = HostInfraUtilizationView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')


def get_credentials_from_config(credential_config_name):
    creds = conf.credentials[credential_config_name]
    username = ("{}\\{}".format(creds.domain, creds.username) if creds.get('domain') else
                creds.username)
    return Host.Credential(principal=username, secret=creds["password"])
