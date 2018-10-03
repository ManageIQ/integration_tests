import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic_patternfly import Input, BootstrapSelect, Button, Dropdown
from widgetastic_manageiq import SummaryFormItem, Table
from widgetastic.exceptions import RowNotFound
from widgetastic.widget import View, Text

from cfme.base.ui import ServerDiagnosticsView
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.timeutil import parsetime
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for


# ============================ Diagnostic Server Workers ===========================

class DiagnosticServerWorkersToolbar(View):
    configuration = Dropdown('Configuration')
    reload_button = Button(id='refresh_workers')


class DiagnosticServerWorkersView(ServerDiagnosticsView):
    toolbar = View.nested(DiagnosticServerWorkersToolbar)
    workers_table = Table('//div[@id="diagnostics_workers"]//table')

    @property
    def is_displayed(self):
        return (
            self.workers.is_displayed and
            self.workers.is_active and
            self.title.text == 'Diagnostics Server "{} [{}]" (current)'.format(
                self.context['object'].name, self.context['object'].sid)
        )


@attr.s
class DiagnosticWorker(BaseEntity):
    """ A class representing Server DiagnosticWorker in the UI.

         Args:
             name : Worker name
             description: Worker description
    """
    name = attr.ib()
    description = attr.ib(default=None)

    def get_all_worker_pids(self):
        """ Returns a list of pids for worker """
        view = navigate_to(self.parent, 'AllDiagnosticWorkers')
        return (
            {row.pid.text for row in view.workers_table.rows() if self.name in row.name.text}
        )

    def reload_worker(self, pid=None):
        """ Reload workers

            Args:
                pid: worker PID, can be passed as a single value or a list of pids

            Returns: Workers pid(list)
        """
        if not pid:
            pid = self.get_all_worker_pids()
        elif not isinstance(pid, (list, set)):
            pid = list(pid)
        view = navigate_to(self.parent, 'AllDiagnosticWorkers')
        # Initiate the restart
        for pid_item in pid:
            row = view.workers_table.row(pid=pid_item)
            if self.appliance.version >= '5.9':
                row[0].check(),
            else:
                row.click()
            view.toolbar.configuration.item_select("Restart selected worker", handle_alert=True)
        return pid

    def check_workers_finished(self, pid):
        """ Check if workers with pid is in the table

            Args:
                pid: worker pid, if multiple pids, pass as a list

         """
        view = self.create_view(DiagnosticServerWorkersView)
        if not isinstance(pid, (list, set)):
            pid = list(pid)
        for pid_item in pid:
            try:
                view.workers_table.row(pid=pid_item)
                return False
            except RowNotFound:
                return True


@attr.s
class DiagnosticWorkersCollection(BaseCollection):
    """Collection object for the :py:class:`DiagnosticWorker`."""
    ENTITY = DiagnosticWorker

    def get_all_pids(self):
        """ Returns(dict): all workers with theirs pids """
        view = navigate_to(self, 'AllDiagnosticWorkers')
        return {row.name.text: row.pid.text for row in view.workers_table.rows()}

    def reload_workers_page(self):
        """ Reload workers page """
        view = navigate_to(self, 'AllDiagnosticWorkers')
        view.toolbar.reload_button.click()


@navigator.register(DiagnosticWorkersCollection, 'AllDiagnosticWorkers')
class AllDiagnosticWorkers(CFMENavigateStep):
    VIEW = DiagnosticServerWorkersView
    prerequisite = NavigateToAttribute('appliance.server', 'Diagnostics')

    def step(self):
        self.prerequisite_view.workers.select()


# ===================== Collect Logs Base ========================================

class CollectLogsBase(Pretty, NavigatableMixin, Updateable):
    """ This class represents the 'Collect logs' base for the server and zone.

        Args:
            appliance: testing appliance
            depot_type: depot type
            depot_name: depot name
            uri: depot uri
            username: depot username
            password: depot password
            second_server_collect: Set True to use slave server
            zone_collect: Set True to collect logs for zone

    """

    _depot_types = dict(
        anon_ftp="Anonymous FTP",
        ftp="FTP",
        nfs="NFS",
        smb="Samba",
        dropbox="Red Hat Dropbox"
    )

    def __init__(self, appliance, depot_type=None, depot_name=None, uri=None, username=None,
                 password=None, second_server_collect=False, zone_collect=False):
        self.depot_name = depot_name
        self.uri = uri
        self.username = username
        self.password = password
        self.depot_type = depot_type
        self.zone_collect = zone_collect
        self.second_server_collect = second_server_collect
        self.appliance = appliance

    def update(self, updates, cancel=False, reset=False):
        """ Updates configuration for collect logs

            Args:
                updates: dict with values to be updated
                cancel: Set True for changes to be canceled
                reset: Set True for changes to be reset


        """
        depot_type = self._depot_types[updates.get('depot_type')]
        try:
            self.second_server_collect = updates.get('second_server_collect')
        except TypeError:
            logger.info('Second Server is not given for update')
        if self.second_server_collect and not self.zone_collect:
            view = navigate_to(self, 'DiagnosticsCollectLogsEditSlave')
        else:
            view = navigate_to(self, 'DiagnosticsCollectLogsEdit')
        view.fill({'depot_type': depot_type})
        fill_dict = {}
        if depot_type != 'Red Hat Dropbox':
            fill_dict.update({'depot_info': {
                'depot_name': updates.get('depot_name'),
                'uri': updates.get('uri')}
            })
        if depot_type in ['FTP', 'Samba']:
            fill_dict.update({'depot_creds': {
                'username': updates.get('username'),
                'password': updates.get('password')
            }
            })
            if self.appliance.version < '5.9':
                fill_dict['depot_creds']['confirm_password'] = updates.get('password')
        updated = view.fill(fill_dict)
        try:
            view.depot_creds.validate_button.click()
            view.flash.assert_message('Log Depot Settings were validated')
        except Exception:
            logger.info('Validate button')
        if reset:
            view.reset_button.click()
            flash_message = 'All changes have been reset'
            flash_view = ServerCollectLogsEditView
        if cancel:
            view.cancel_button.click()
            flash_view = ServerCollectLogsView
            flash_message = "Edit Log Depot settings was cancelled by the user"
        elif updated:
            view.save_button.click()
            flash_view = ServerCollectLogsView
            flash_message = "Log Depot Settings were saved"
        else:
            logger.info('Settings were not updated')
        view = self.create_view(flash_view)
        view.flash.assert_message(flash_message)

    @property
    def last_collection(self):
        """
            Returns: None if logs were not collected or
                :py:class`utils.timeutil.datetime()`, time were last collection took place
        """
        if self.second_server_collect and not self.zone_collect:
            view = navigate_to(self, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self, 'DiagnosticsCollectLogs')
        text = view.last_log_collection.read()
        if text.lower() == "never":
            return None
        else:
            try:
                return parsetime.from_american_with_utc(text)
            except ValueError:
                return parsetime.from_iso_with_utc(text)

    @property
    def is_cleared(self):
        """ Checks if configuration is set to default

            Returns: True if settings is default, and False if not
        """
        if self.second_server_collect and not self.zone_collect:
            view = navigate_to(self, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self, 'DiagnosticsCollectLogs')
        return view.log_depot_uri.read() == "N/A"

    def clear(self):
        """ Set depot type to "No Depot" """
        if not self.is_cleared:
            if self.second_server_collect and not self.zone_collect:
                view = navigate_to(self, 'DiagnosticsCollectLogsEditSlave', wait_for_view=True)
            else:
                view = navigate_to(self, 'DiagnosticsCollectLogsEdit', wait_for_view=True)
            view.depot_type.fill('<No Depot>')
            view.save_button.click()
            view = self.create_view(ServerCollectLogsView)
            view.flash.assert_message("Log Depot Settings were saved")

    def _collect(self, selection):
        """ Initiate and wait for collection to finish.

            Args:
                selection: The item in Collect menu ('Collect all logs' or 'Collect current logs')
        """
        if self.second_server_collect and not self.zone_collect:
            view = navigate_to(self, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self, 'DiagnosticsCollectLogs')
        last_collection = self.last_collection
        # Initiate the collection
        view.toolbar.collect.item_select(selection)
        slave_servers = self.appliance.server.slave_servers
        first_slave_server = slave_servers[0] if slave_servers else None

        if self.zone_collect:
            message = "Zone {}".format(self.appliance.server.zone.name)
        elif self.second_server_collect:
            message = "MiqServer {} [{}]".format(
                first_slave_server.name,
                first_slave_server.sid
            )
        else:
            message = "MiqServer {} [{}]".format(
                self.appliance.server.name,
                self.appliance.server.zone.id
            )
        view.flash.assert_message(
            "Log collection for {} {} has been initiated".format(
                self.appliance.product_name, message))

        # Wait for start
        if last_collection is not None:
            # How does this work?
            # The time is updated just after the collection has started
            # If the Text is Never, we will not wait as there is nothing in the last message.
            wait_for(
                lambda: self.last_collection > last_collection,
                num_sec=4 * 60,
                fail_func=self.browser.refresh,
                message="wait_for_log_collection_start"
            )
        # Wait for finish
        wait_for(
            lambda: "were successfully collected" in self.last_message,
            num_sec=4 * 60,
            fail_func=self.browser.refresh,
            message="wait_for_log_collection_finish"
        )

    def collect_all(self):
        """ Initiate and wait for collection of all logs to finish. """

        self._collect("Collect all logs")

    def collect_current(self):
        """ Initiate and wait for collection of the current log to finish. """

        self._collect("Collect current logs")


# ======================= Server Collect Logs ============================

class ServerCollectLogsToolbar(View):
    edit = Button(title="Edit the Log Depot settings for the selected Server")
    collect = Dropdown('Collect Logs')


class ServerCollectLogsView(ServerDiagnosticsView):
    toolbar = View.nested(ServerCollectLogsToolbar)

    log_depot_uri = SummaryFormItem('Basic Info', 'Log Depot URI')
    last_log_collection = SummaryFormItem('Basic Info', 'Last Log Collection')
    last_log_message = SummaryFormItem('Basic Info', 'Last Message')

    @property
    def is_displayed(self):
        return (
            self.in_server_collect_logs and
            self.title.text == 'Diagnostics Server "{} [{}]" (current)'.format(
                self.context['object'].name, self.context['object'].sid)
        )

    @property
    def in_server_collect_logs(self):
        return (
            self.collectlogs.is_displayed and
            self.collectlogs.is_active()
        )


class CollectLogsBasicEntities(View):
    depot_name = Input(name='depot_name')
    uri = Input(name='uri')


class CollectLogsCredsEntities(View):
    username = Input(name='log_userid')
    password = Input(name='log_password')
    confirm_password = Input(name='log_verify')
    validate_button = Button('Validate')


class ServerCollectLogsEditView(ServerCollectLogsView):
    edit_form_title = Text('//form[@id="form_div"]/h3')
    depot_type = BootstrapSelect(id='log_protocol')
    depot_info = View.nested(CollectLogsBasicEntities)
    depot_creds = View.nested(CollectLogsCredsEntities)

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return(
            self.in_server_collect_logs and
            self.depot_type.is_displayed and
            ('Editing Log Depot Settings for Server'in self.edit_form_title.text or
             'Editing Log Depot Settings for Zone' in self.edit_form_title.text)
        )


class ServerCollectLog(CollectLogsBase):
    """ Represents Server Collect Log settings """
    def __init__(self, appliance):
        self.appliance = appliance
        CollectLogsBase.__init__(self, appliance=appliance)

    @property
    def last_message(self):
        """
            Return: Message value for server collect logs
        """
        if self.second_server_collect:
            view = navigate_to(self, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self, 'DiagnosticsCollectLogs')
        return view.last_log_message.read()


# ====================== Zone Collect Logs ===================================

class ZoneCollectLogToolbar(View):
    configuration = Dropdown('Configuration')
    edit = Button(title="Edit the Log Depot settings for the selected Zone")
    collect = Dropdown('Collect Logs')


class ZoneDiagnosticsCollectLogsView(ServerDiagnosticsView):
    toolbar = View.nested(ZoneCollectLogToolbar)

    log_depot_uri = SummaryFormItem('Basic Info', 'Log Depot URI')
    last_log_collection = SummaryFormItem('Basic Info', 'Last Log Collection')

    @property
    def is_displayed(self):
        return (
            self.collectlogs.is_displayed and
            self.collectlogs.is_active and
            self.title.text == 'Diagnostics Zone "{}" (current)'.format(
                self.context['object'].description))


class ZoneCollectLog(CollectLogsBase):
    """ Represents Zone Collect Log settings """
    def __init__(self, appliance):
        self.appliance = appliance
        CollectLogsBase.__init__(self, appliance=appliance, zone_collect=True)

    # Zone doesn't have Las log message info,
    # but need to check if logs are collected for servers under zone
    @property
    def last_message(self):
        if self.second_server_collect:
            view = navigate_to(self.appliance.server.collect_logs, 'DiagnosticsCollectLogsSlave')
        else:
            view = navigate_to(self.appliance.server.collect_logs, 'DiagnosticsCollectLogs')
        return view.last_log_message.read()


# ==================== Server/Zone Collect Logs Steps =========================

@navigator.register(ServerCollectLog)
class DiagnosticsSummary(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToAttribute('appliance.server', 'Diagnostics')

    def step(self):
        self.prerequisite_view.summary.select()


@navigator.register(ServerCollectLog, "DiagnosticsCollectLogs")
class DiagnosticsCollectLogs(CFMENavigateStep):
    VIEW = ServerCollectLogsView
    prerequisite = NavigateToAttribute('appliance.server', 'Diagnostics')

    def step(self):
        self.prerequisite_view.collectlogs.select()


@navigator.register(ServerCollectLog, "DiagnosticsCollectLogsSlave")
class DiagnosticsCollectLogsSlave(CFMENavigateStep):
    VIEW = ServerCollectLogsView
    prerequisite = NavigateToAttribute('appliance.server', 'Diagnostics')

    def step(self):
        slave_server = self.appliance.server.slave_servers[0]
        self.prerequisite_view.accordions.diagnostics.tree.click_path(
            self.appliance.server_region_string(),
            "Zone: {} (current)".format(self.appliance.server.zone.description),
            "Server: {} [{}]".format(slave_server.name,
                                     int(slave_server.sid)))
        self.prerequisite_view.collectlogs.select()


@navigator.register(ServerCollectLog, "DiagnosticsCollectLogsEdit")
@navigator.register(ZoneCollectLog, "DiagnosticsCollectLogsEdit")
class DiagnosticsCollectLogsEdit(CFMENavigateStep):
    VIEW = ServerCollectLogsEditView
    prerequisite = NavigateToSibling('DiagnosticsCollectLogs')

    def step(self):
        self.prerequisite_view.toolbar.edit.click()


@navigator.register(ServerCollectLog, "DiagnosticsCollectLogsEditSlave")
class DiagnosticsCollectLogsEditSlave(CFMENavigateStep):
    VIEW = ServerCollectLogsEditView
    prerequisite = NavigateToSibling('DiagnosticsCollectLogsSlave')

    def step(self):
        self.prerequisite_view.toolbar.edit.click()


@navigator.register(ZoneCollectLog, 'DiagnosticsCollectLogs')
class ZoneDiagnosticsCollectLogs(CFMENavigateStep):
    VIEW = ZoneDiagnosticsCollectLogsView
    prerequisite = NavigateToAttribute('appliance.server.zone', 'Diagnostics')

    def step(self):
        self.prerequisite_view.collectlogs.select()
