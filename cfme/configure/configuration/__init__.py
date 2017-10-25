# -*- coding: utf-8 -*-
from functools import partial

from cfme.base.ui import Region, Zone
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from cfme.web_ui import (Form, InfoBlock, Input, Region as UIRegion, Table, accordion,
                         fill, form_buttons)
from cfme.web_ui.form_buttons import change_stored_password
from cfme.utils import conf
from cfme.utils.appliance import Navigatable, current_appliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.pretty import Pretty
from cfme.utils.timeutil import parsetime
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

depot_types = dict(
    anon_ftp="Anonymous FTP",
    ftp="FTP",
    nfs="NFS",
    smb="Samba",
    dropbox="Red Hat Dropbox",
)


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
