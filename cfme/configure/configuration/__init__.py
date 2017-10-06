# -*- coding: utf-8 -*-
from navmazing import NavigateToAttribute, NavigateToSibling, NavigateToObject

from contextlib import contextmanager
from fixtures.pytest_store import store
from functools import partial

from cfme.base.ui import Server, Region, Zone
from cfme.exceptions import (
    AuthModeUnknown,
    ConsoleNotSupported,
    ConsoleTypeNotSupported,
    ScheduleNotFound)
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.web_ui import (
    AngularSelect, Calendar, CFMECheckbox, Form, InfoBlock, Input,
    Region as UIRegion, Select, Table, accordion, fill, flash, form_buttons)
from cfme.web_ui.form_buttons import change_stored_password
from cfme.utils import version, conf
from cfme.utils.appliance import Navigatable, current_appliance
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.timeutil import parsetime
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for, TimedOutError


access_tree = partial(accordion.tree, "Access Control")
database_tree = partial(accordion.tree, "Database")
settings_tree = partial(accordion.tree, "Settings")
diagnostics_tree = partial(accordion.tree, "Diagnostics")

replication_worker = Form(
    fields=[
        ('database', Input("replication_worker_dbname")),
        ('port', Input("replication_worker_port")),
        ('username', Input("replication_worker_username")),
        ('password', Input("replication_worker_password")),
        ('password_verify', Input("replication_worker_verify")),
        ('host', Input("replication_worker_host")),
    ]
)

replication_process = UIRegion(locators={
    "status": InfoBlock("Replication Process", "Status"),
    "current_backlog": InfoBlock("Replication Process", "Current Backlog"),
})

server_roles = Form(
    fields=[
        # TODO embedded_ansible is only present in CFME 5.8 (MIQ Fine+)
        ('embedded_ansible', CFMECheckbox("server_roles_embedded_ansible")),
        ('ems_metrics_coordinator', CFMECheckbox("server_roles_ems_metrics_coordinator")),
        ('ems_operations', CFMECheckbox("server_roles_ems_operations")),
        ('ems_metrics_collector', CFMECheckbox("server_roles_ems_metrics_collector")),
        ('reporting', CFMECheckbox("server_roles_reporting")),
        ('ems_metrics_processor', CFMECheckbox("server_roles_ems_metrics_processor")),
        ('scheduler', CFMECheckbox("server_roles_scheduler")),
        ('smartproxy', CFMECheckbox("server_roles_smartproxy")),
        ('database_operations', CFMECheckbox("server_roles_database_operations")),
        ('smartstate', CFMECheckbox("server_roles_smartstate")),
        ('event', CFMECheckbox("server_roles_event")),
        ('user_interface', CFMECheckbox("server_roles_user_interface")),
        ('web_services', CFMECheckbox("server_roles_web_services")),
        ('ems_inventory', CFMECheckbox("server_roles_ems_inventory")),
        ('notifier', CFMECheckbox("server_roles_notifier")),
        ('automate', CFMECheckbox("server_roles_automate")),
        ('rhn_mirror', CFMECheckbox("server_roles_rhn_mirror")),
        ('database_synchronization', CFMECheckbox("server_roles_database_synchronization")),
        ('git_owner', CFMECheckbox("server_roles_git_owner")),
        ('websocket', CFMECheckbox("server_roles_websocket")),
        ('cockpit_ws', CFMECheckbox("server_roles_cockpit_ws")),
        # STORAGE OPTIONS
        ("storage_metrics_processor", CFMECheckbox("server_roles_storage_metrics_processor")),
        ("storage_metrics_collector", CFMECheckbox("server_roles_storage_metrics_collector")),
        ("storage_metrics_coordinator", CFMECheckbox("server_roles_storage_metrics_coordinator")),
        ("storage_inventory", CFMECheckbox("server_roles_storage_inventory")),
        ("vmdb_storage_bridge", CFMECheckbox("server_roles_vmdb_storage_bridge")),

    ]
)

ntp_servers = Form(
    fields=[
        ('ntp_server_1', Input("ntp_server_1")),
        ('ntp_server_2', Input("ntp_server_2")),
        ('ntp_server_3', Input("ntp_server_3")),
    ]
)

depot_types = dict(
    anon_ftp="Anonymous FTP",
    ftp="FTP",
    nfs="NFS",
    smb="Samba",
    dropbox="Red Hat Dropbox",
)

db_configuration = Form(
    fields=[
        ('type', Select("select#production_dbtype")),
        ('hostname', Input("production_host")),
        ('database', Input("production_database")),
        ('username', Input("production_username")),
        ('password', Input("production_password")),
        ('password_verify', Input("production_verify")),
    ]
)

category_form = Form(
    fields=[
        ('new_tr', "//tr[@id='new_tr']"),
        ('name', Input("name")),
        ('display_name', Input("description")),
        ('description', Input("example_text")),
        ('show_in_console', CFMECheckbox("show")),
        ('single_value', CFMECheckbox("single_value")),
        ('capture_candu', CFMECheckbox("perf_by_tag"))
    ])

tag_form = Form(
    fields=[
        ('category', {
            version.LOWEST: Select("select#classification_name"),
            '5.5': AngularSelect('classification_name')}),
        ('name', Input("entry[name]")),
        ('display_name', Input("entry[description]")),
        ('add', {
            version.LOWEST: Input("accept"),
            '5.6': '//button[normalize-space(.)="Add"]'
        }),
        ('new', {
            version.LOWEST: "//span[@class='glyphicon glyphicon-plus']",
            '5.6': '//button[normalize-space(.)="Add"]'
        }),
        ('save', '//button[normalize-space(.)="Save"]'),
    ])


records_table = Table("//div[@id='records_div']/table")
category_table = Table("//div[@id='settings_co_categories']/table")
classification_table = Table("//div[@id='classification_entries_div']/table")


class ServerLogDepot(Pretty, Navigatable):
    """ This class represents the 'Collect logs' for the server.

    Usage:

        log_credentials = configure.ServerLogDepot("anon_ftp",
                                               depot_name=fauxfactory.gen_alphanumeric(),
                                               uri=fauxfactory.gen_alphanumeric())
        log_credentials.create()
        log_credentials.clear()

    """

    def __init__(self, depot_type, depot_name=None, uri=None, username=None, password=None,
                 zone_collect=False, second_server_collect=False, appliance=None):
        self.depot_name = depot_name
        self.uri = uri
        self.username = username
        self.password = password
        self.depot_type = depot_types[depot_type]
        self.zone_collect = zone_collect
        self.second_server_collect = second_server_collect
        Navigatable.__init__(self, appliance=appliance)

        self.obj_type = Zone(self.appliance) if self.zone_collect else self.appliance.server

    def create(self, cancel=False):
        self.clear()
        if self.second_server_collect and not self.zone_collect:
            view = navigate_to(self.appliance.server, 'DiagnosticsCollectLogsEditSlave')
        else:
            view = navigate_to(self.obj_type, 'DiagnosticsCollectLogsEdit')
        view.fill({'depot_type': self.depot_type})
        if self.depot_type != 'Red Hat Dropbox':
            view.fill({'depot_name': self.depot_name,
                       'uri': self.uri})
        if self.depot_type in ['FTP', 'Samba']:
            view.fill({'username': self.username,
                       'password': self.password,
                       'confirm_password': self.password})
            view.validate.click()
            view.flash.assert_success_message("Log Depot Settings were validated")
        if cancel:
            view.cancel.click()
            view.flash.assert_success_message("Edit Log Depot settings was cancelled by the user")
        else:
            view.save.click()
            view.flash.assert_success_message("Log Depot Settings were saved")

    @property
    def last_collection(self):
        if self.second_server_collect and not self.zone_collect:
            view = navigate_to(self.appliance.server, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self.obj_type, 'DiagnosticsCollectLogs')
        text = view.last_log_collection.text
        if text.lower() == "never":
            return None
        else:
            try:
                return parsetime.from_american_with_utc(text)
            except ValueError:
                return parsetime.from_iso_with_utc(text)

    @property
    def last_message(self):
        if self.second_server_collect:
            view = navigate_to(self.appliance.server, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self.appliance.server, 'DiagnosticsCollectLogs')
        return view.last_log_message.text

    @property
    def is_cleared(self):
        if self.second_server_collect and not self.zone_collect:
            view = navigate_to(self.appliance.server, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self.obj_type, 'DiagnosticsCollectLogs')
        return view.log_depot_uri.text == "N/A"

    def clear(self):
        """ Set depot type to "No Depot"

        """
        if not self.is_cleared:
            if self.second_server_collect and not self.zone_collect:
                view = navigate_to(self.appliance.server, 'DiagnosticsCollectLogsEditSlave')
            else:
                view = navigate_to(self.obj_type, 'DiagnosticsCollectLogsEdit')
            if BZ.bugzilla.get_bug(1436326).is_opened:
                wait_for(lambda: view.depot_type.selected_option != '<No Depot>', num_sec=5)
            view.depot_type.fill('<No Depot>')
            view.save.click()
            view.flash.assert_success_message("Log Depot Settings were saved")

    def _collect(self, selection):
        """ Initiate and wait for collection to finish.

        Args:
            selection: The item in Collect menu ('Collect all logs' or 'Collect current logs')
        """

        if self.second_server_collect and not self.zone_collect:
            view = navigate_to(self.appliance.server, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self.obj_type, 'DiagnosticsCollectLogs')
        last_collection = self.last_collection
        # Initiate the collection
        tb.select("Collect", selection)
        if self.zone_collect:
            message = "Zone {}".format(self.obj_type.name)
        elif self.second_server_collect:
            message = "MiqServer {} [{}]".format(
                self.appliance.slave_server_name(), self.appliance.slave_server_zone_id())
        else:
            message = "MiqServer {} [{}]".format(
                self.appliance.server_name(), self.appliance.server_zone_id())
        view.flash.assert_success_message(
            "Log collection for {} {} has been initiated".
            format(self.appliance.product_name, message))

        def _refresh():
            """ The page has no refresh button, so we'll switch between tabs.

            Why this? Selenium's refresh() is way too slow. This is much faster.

            """
            if self.zone_collect:
                navigate_to(self.obj_type, 'Servers')
            else:
                navigate_to(self.obj_type, 'Workers')
            if self.second_server_collect:
                navigate_to(self.appliance.server, 'DiagnosticsCollectLogsSlave')
            else:
                navigate_to(self.appliance.server, 'DiagnosticsCollectLogs')

        # Wait for start
        if last_collection is not None:
            # How does this work?
            # The time is updated just after the collection has started
            # If the Text is Never, we will not wait as there is nothing in the last message.
            wait_for(
                lambda: self.last_collection > last_collection,
                num_sec=90,
                fail_func=_refresh,
                message="wait_for_log_collection_start"
            )
        # Wait for finish
        wait_for(
            lambda: "were successfully collected" in self.last_message,
            num_sec=4 * 60,
            fail_func=_refresh,
            message="wait_for_log_collection_finish"
        )

    def collect_all(self):
        """ Initiate and wait for collection of all logs to finish.

        """
        self._collect("Collect all logs")

    def collect_current(self):
        """ Initiate and wait for collection of the current log to finish.

        """
        self._collect("Collect current logs")


class Schedule(Pretty, Navigatable):
    """ Configure/Configuration/Region/Schedules functionality

    Create, Update, Delete functionality.

    Args:
        name: Schedule's name.
        description: Schedule description.
        active: Whether the schedule should be active (default `True`)
        action: Action type
        filter_type: Filtering type
        filter_value: If a more specific `filter_type` is selected, here is the place to choose
            hostnames, machines and so ...
        run_type: Once, Hourly, Daily, ...
        run_every: If `run_type` is not Once, then you can specify how often it should be run.
        time_zone: Time zone selection.
        start_date: Specify start date (mm/dd/yyyy or datetime.datetime()).
        start_hour: Starting hour
        start_min: Starting minute.

    Usage:

        schedule = Schedule(
            "My very schedule",
            "Some description here.",
            action="Datastore Analysis",
            filter_type="All Datastores for Host",
            filter_value="datastore.intra.acme.com",
            run_type="Hourly",
            run_every="2 Hours"
        )
        schedule.create()
        schedule.disable()
        schedule.enable()
        schedule.delete()
        # Or
        Schedule.enable_by_names("One schedule", "Other schedule")
        # And so.

    Note: TODO: Maybe the row handling might go into Table class?

    """
    tab = {"Hourly": "timer_hours",
           "Daily": "timer_days",
           "Weekly": "timer_weeks",
           "Monthly": "timer_months"}

    form = Form(fields=[
        ("name", Input("name")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("action", {
            version.LOWEST: Select("select#action_typ"),
            '5.5': AngularSelect('action_typ')}),
        ("filter_type", {
            version.LOWEST: Select("select#filter_typ"),
            '5.5': AngularSelect('filter_typ')}),
        ("filter_value", {
            version.LOWEST: Select("select#filter_value"),
            '5.5': AngularSelect('filter_value')}),
        ("timer_type", {
            version.LOWEST: Select("select#timer_typ"),
            '5.5': AngularSelect('timer_typ')}),
        ("timer_hours", Select("select#timer_hours")),
        ("timer_days", Select("select#timer_days")),
        ("timer_weeks", Select("select#timer_weekss")),    # Not a typo!
        ("timer_months", Select("select#timer_months")),
        ("timer_value", AngularSelect('timer_value'), {"appeared_in": "5.5"}),
        ("time_zone", {
            version.LOWEST: Select("select#time_zone"),
            '5.5': AngularSelect('time_zone')}),
        ("start_date", Calendar("miq_angular_date_1")),
        ("start_hour", {
            version.LOWEST: Select("select#start_hour"),
            '5.5': AngularSelect('start_hour')}),
        ("start_min", {
            version.LOWEST: Select("select#start_min"),
            '5.5': AngularSelect('start_min')}),
    ])

    pretty_attrs = ['name', 'description', 'run_type', 'run_every',
                    'start_date', 'start_hour', 'start_min']

    def __init__(self, name, description, active=True, action=None, filter_type=None,
                 filter_value=None, run_type="Once", run_every=None, time_zone=None,
                 start_date=None, start_hour=None, start_min=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.details = dict(
            name=name,
            description=description,
            active=active,
            action=action,
            filter_type=filter_type,
            filter_value=filter_value,
            time_zone=sel.ByValue(time_zone),
            start_date=start_date,
            start_hour=start_hour,
            start_min=start_min,
        )

        if run_type == "Once":
            self.details["timer_type"] = "Once"
        else:
            field = version.pick({
                version.LOWEST: self.tab[run_type],
                '5.5': 'timer_value'})
            self.details["timer_type"] = run_type
            self.details[field] = run_every

    def create(self, cancel=False):
        """ Create a new schedule from the informations stored in the object.

        Args:
            cancel: Whether to click on the cancel button to interrupt the creation.
        """
        navigate_to(self, 'Add')

        if cancel:
            action = form_buttons.cancel
        else:
            action = form_buttons.add
        fill(
            self.form,
            self.details,
            action=action
        )

    def update(self, updates, cancel=False):
        """ Modify an existing schedule with informations from this instance.

        Args:
            updates: Dict with fields to be updated
            cancel: Whether to click on the cancel button to interrupt the editation.

        """
        navigate_to(self, 'Edit')

        if cancel:
            action = form_buttons.cancel
        else:
            action = form_buttons.save
        self.details.update(updates)
        fill(
            self.form,
            self.details,
            action=action
        )

    def delete(self, cancel=False):
        """ Delete the schedule represented by this object.

        Calls the class method with the name of the schedule taken out from the object.

        Args:
            cancel: Whether to click on the cancel button in the pop-up.
        """
        navigate_to(self, 'Details')
        tb.select("Configuration", "Delete this Schedule from the Database", invokes_alert=True)
        sel.handle_alert(cancel)

    def enable(self):
        """ Enable the schedule via table checkbox and Configuration menu.

        """
        self.select()
        tb.select("Configuration", "Enable the selected Schedules")

    def disable(self):
        """ Enable the schedule via table checkbox and Configuration menu.

        """
        self.select()
        tb.select("Configuration", "Disable the selected Schedules")

    def select(self):
        """ Select the checkbox for current schedule

        """
        navigate_to(self, 'All')
        for row in records_table.rows():
            if row.name.strip() == self.details['name']:
                checkbox = row[0].find_element_by_xpath("//input[@type='checkbox']")
                if not checkbox.is_selected():
                    sel.click(checkbox)
                break
        else:
            raise ScheduleNotFound(
                "Schedule '{}' could not be found for selection!".format(self.details['name'])
            )


@navigator.register(Schedule, 'All')
class ScheduleAll(CFMENavigateStep):
    prerequisite = NavigateToObject(Server, 'Configuration')

    def step(self):
        server_region = store.current_appliance.server_region_string()
        self.prerequisite_view.accordions.settings.tree.click_path(server_region, "Schedules")


@navigator.register(Schedule, 'Add')
class ScheduleAdd(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        tb.select("Configuration", "Add a new Schedule")


@navigator.register(Schedule, 'Details')
class ScheduleDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        records_table.click_cell("name", self.obj.details["name"])


@navigator.register(Schedule, 'Edit')
class ScheduleEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        tb.select("Configuration", "Edit this Schedule")


class DatabaseBackupSchedule(Schedule):
    """ Configure/Configuration/Region/Schedules - Database Backup type

    Args:
        name: Schedule name
        description: Schedule description
        active: Whether the schedule should be active (default `True`)
        protocol: One of ``{'Samba', 'Network File System'}``
        run_type: Once, Hourly, Daily, ...
        run_every: If `run_type` is not Once, then you can specify how often it should be run
        time_zone: Time zone selection
        start_date: Specify start date (mm/dd/yyyy or datetime.datetime())
        start_hour: Starting hour
        start_min: Starting minute

    Usage:
        smb_schedule = DatabaseBackupSchedule(
            name="Bi-hourly Samba Database Backup",
            description="Everybody's favorite backup schedule",
            protocol="Samba",
            uri="samba.example.com/share_name",
            username="samba_user",
            password="secret",
            password_verify="secret",
            time_zone="UTC",
            start_date=datetime.datetime.utcnow(),
            run_type="Hourly",
            run_every="2 Hours"
        )
        smb_schedule.create()
        smb_schedule.delete()

        ... or ...

        nfs_schedule = DatabaseBackupSchedule(
            name="One-time NFS Database Backup",
            description="The other backup schedule",
            protocol="Network File System",
            uri="nfs.example.com/path/to/share",
            time_zone="Chihuahua",
            start_date="21/6/2014",
            start_hour="7",
            start_min="45"
        )
        nfs_schedule.create()
        nfs_schedule.delete()

    """
    form = Form(fields=[
        ("name", Input("name")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("action", {
            version.LOWEST: Select("select#action_typ"),
            '5.5': AngularSelect('action_typ')}),
        ("log_protocol", {
            version.LOWEST: Select("select#log_protocol"),
            '5.5': AngularSelect('log_protocol')}),
        ("depot_name", Input("depot_name")),
        ("uri", Input("uri")),
        ("log_userid", Input("log_userid")),
        ("log_password", Input("log_password")),
        ("log_verify", Input("log_verify")),
        ("timer_type", {
            version.LOWEST: Select("select#timer_typ"),
            '5.5': AngularSelect('timer_typ')}),
        ("timer_hours", Select("select#timer_hours")),
        ("timer_days", Select("select#timer_days")),
        ("timer_weeks", Select("select#timer_weekss")),    # Not a typo!
        ("timer_months", Select("select#timer_months")),
        ("timer_value", AngularSelect('timer_value'), {"appeared_in": "5.5"}),
        ("time_zone", AngularSelect('time_zone')),
        ("start_date", Calendar("start_date")),
        ("start_hour", AngularSelect('start_hour')),
        ("start_min", AngularSelect('start_min')),
    ])

    def __init__(self, name, description, active=True, protocol=None, depot_name=None, uri=None,
                 username=None, password=None, password_verify=None, run_type="Once",
                 run_every=None, time_zone=None, start_date=None, start_hour=None, start_min=None):

        assert protocol in {'Samba', 'Network File System'},\
            "Unknown protocol type '{}'".format(protocol)

        if protocol == 'Samba':
            self.details = dict(
                name=name,
                description=description,
                active=active,
                action='Database Backup',
                log_protocol=sel.ByValue(protocol),
                depot_name=depot_name,
                uri=uri,
                log_userid=username,
                log_password=password,
                log_verify=password_verify,
                time_zone=sel.ByValue(time_zone),
                start_date=start_date,
                start_hour=start_hour,
                start_min=start_min,
            )
        else:
            self.details = dict(
                name=name,
                description=description,
                active=active,
                action='Database Backup',
                log_protocol=sel.ByValue(protocol),
                depot_name=depot_name,
                uri=uri,
                time_zone=sel.ByValue(time_zone),
                start_date=start_date,
                start_hour=start_hour,
                start_min=start_min,
            )

        if run_type == "Once":
            self.details["timer_type"] = "Once"
        else:
            field = version.pick({
                version.LOWEST: self.tab[run_type],
                '5.5': 'timer_value'})
            self.details["timer_type"] = run_type
            self.details[field] = run_every

    def create(self, cancel=False, samba_validate=False):
        """ Create a new schedule from the informations stored in the object.

        Args:
            cancel: Whether to click on the cancel button to interrupt the creation.
            samba_validate: Samba-only option to click the `Validate` button to check
                            if entered samba credentials are valid or not
        """
        navigate_to(self, 'Add')

        fill(self.form, self.details)
        if samba_validate:
            sel.click(form_buttons.validate)
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.add()
            flash.assert_message_contain(
                'Schedule "{}" was saved'.format(self.details['name']))

    def update(self, updates, cancel=False, samba_validate=False):
        """ Modify an existing schedule with informations from this instance.

        Args:
            updates: Dict with fields to be updated
            cancel: Whether to click on the cancel button to interrupt the editation.
            samba_validate: Samba-only option to click the `Validate` button to check
                            if entered samba credentials are valid or not
        """
        navigate_to(self, 'Edit')

        self.details.update(updates)
        fill(self.form, self.details)
        if samba_validate:
            sel.click(form_buttons.validate)
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.save()

    def delete(self):
        super(DatabaseBackupSchedule, self).delete()
        flash.assert_message_contain(
            'Schedule "{}": Delete successful'.format(self.details['description'])
        )

    @property
    def last_date(self):
        navigate_to(self, 'All')
        name = self.details["name"]
        row = records_table.find_row("Name", name)
        return row[6].text


def restart_workers(name, wait_time_min=1):
    """ Restarts workers by their name.

    Args:
        name: Name of the worker. Multiple workers can have the same name. Name is matched with `in`
    Returns: bool whether the restart succeeded.
    """

    navigate_to(current_appliance.server, 'DiagnosticsWorkers')

    def get_all_pids(worker_name):
        return {row.pid.text for row in records_table.rows() if worker_name in row.name.text}

    reload_func = partial(tb.select, "Reload current workers display")

    pids = get_all_pids(name)
    # Initiate the restart
    for pid in pids:
        records_table.click_cell("pid", pid)
        tb.select("Configuration", "Restart selected worker", invokes_alert=True)
        sel.handle_alert(cancel=False)
        reload_func()

    # Check they have finished
    def _check_all_workers_finished():
        for pid in pids:
            if records_table.click_cell("pid", pid):    # If could not click, no longer present
                return False                    # If clicked, it is still there so unsuccess
        return True

    # Wait for all original workers to be gone
    try:
        wait_for(
            _check_all_workers_finished,
            fail_func=reload_func,
            num_sec=wait_time_min * 60
        )
    except TimedOutError:
        return False

    # And now check whether the same number of workers is back online
    try:
        wait_for(
            lambda: len(pids) == len(get_all_pids(name)),
            fail_func=reload_func,
            num_sec=wait_time_min * 60,
            message="wait_workers_back_online"
        )
        return True
    except TimedOutError:
        return False


def get_workers_list(do_not_navigate=False, refresh=True):
    """Retrieves all workers.

    Returns a dictionary where keys are names of the workers and values are lists (because worker
    can have multiple instances) which contain dictionaries with some columns.
    """
    if do_not_navigate:
        if refresh:
            tb.select("Reload current workers display")
    else:
        navigate_to(current_appliance.server, 'Workers')
    workers = {}
    for row in records_table.rows():
        name = sel.text_sane(row.name)
        if name not in workers:
            workers[name] = []
        worker = {
            "status": sel.text_sane(row.status),
            "pid": int(sel.text_sane(row.pid)) if len(sel.text_sane(row.pid)) > 0 else None,
            "spid": int(sel.text_sane(row.spid)) if len(sel.text_sane(row.spid)) > 0 else None,
            "started": parsetime.from_american_with_utc(sel.text_sane(row.started)),

            "last_heartbeat": None,
        }
        try:
            workers["last_heartbeat"] = parsetime.from_american_with_utc(
                sel.text_sane(row.last_heartbeat))
        except ValueError:
            pass
        workers[name].append(worker)
    return workers


def set_replication_worker_host(host, port='5432'):
    """ Set replication worker host on Configure / Configuration pages.

    Args:
        host: Address of the hostname to replicate to.
    """
    navigate_to(current_appliance.server, 'Workers')
    change_stored_password()
    fill(
        replication_worker,
        dict(host=host,
             port=port,
             username=conf.credentials['database']['username'],
             password=conf.credentials['database']['password'],
             password_verify=conf.credentials['database']['password']),
        action=form_buttons.save
    )


def get_replication_status(navigate=True):
    """ Gets replication status from Configure / Configuration pages.

    Returns: bool of whether replication is Active or Inactive.
    """
    if navigate:

        navigate_to(Region, 'Replication')
    return replication_process.status.text == "Active"


def get_replication_backlog(navigate=True):
    """ Gets replication backlog from Configure / Configuration pages.

    Returns: int representing the remaining items in the replication backlog.
    """
    if navigate:
        navigate_to(Region, 'Replication')
    return int(replication_process.current_backlog.text)
