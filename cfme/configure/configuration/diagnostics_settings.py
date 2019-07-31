import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import RowNotFound
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.base.ui import ServerDiagnosticsView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.timeutil import parsetime
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import Table


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
                self.context['object'].appliance.server.name,
                self.context['object'].appliance.server.sid)
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
            row[0].check()
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

    def step(self, *args, **kwargs):
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
    # we need to use some name that indicates it is test data
    ALERT_PROMPT = 'test_cfme_can_be_deleted'

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
        updated = view.fill({'depot_type': depot_type})
        fill_dict = {}
        if depot_type != 'Red Hat Dropbox':
            fill_dict.update(
                {
                    'depot_info':
                        {
                            'depot_name': updates.get('depot_name'),
                            'uri': updates.get('uri')
                        }
                }
            )
        else:  # all data is filled automatically for Red Hat Dropbox depot type
            updated = True
        if depot_type in ['FTP', 'Samba']:
            fill_dict.update(
                {
                    'depot_creds':
                        {
                            'username': updates.get('username'),
                            'password': updates.get('password')
                        }
                }
            )
        updated = view.fill(fill_dict) or updated
        try:
            view.depot_creds.validate_button.click()
            view.flash.assert_message('Log Depot Settings were validated')
        except Exception:
            logger.info('Validate button')
        if reset:
            view.reset_button.click()
            flash_message = 'All changes have been reset'
            flash_view = self.edit_view
        if cancel:
            view.cancel_button.click()
            flash_view = self.main_view
            flash_message = "Edit Log Depot settings was cancelled by the user"
        elif updated:
            view.save_button.click()
            flash_view = self.main_view
            flash_message = "Log Depot Settings were saved"
        else:
            logger.info('Settings were not updated')
        view = self.create_view(flash_view, wait=10)  # implicit assert
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
                view = navigate_to(self, 'DiagnosticsCollectLogsEditSlave')
            else:
                view = navigate_to(self, 'DiagnosticsCollectLogsEdit')
            view.depot_type.fill('<No Depot>')
            view.save_button.click()
            view = self.create_view(ServerCollectLogsView)
            view.flash.assert_message("Log Depot Settings were saved")

    def _collect(self, selection):
        """ Initiate and wait for collection to finish.

            Args:
                selection: The item in Collect menu ('Collect all logs' or 'Collect current logs')
        """
        view = navigate_to(
            self,
            'DiagnosticsCollectLogsSlave' if self.second_server_collect and not self.zone_collect
            else 'DiagnosticsCollectLogs')
        last_collection = self.last_collection
        # Initiate the collection
        wait_for(view.toolbar.collect.item_enabled,
                 func_args=[selection],
                 delay=5,
                 timeout=600,
                 handle_exception=True,
                 fail_func=self.browser.refresh)
        view.toolbar.collect.item_select(selection, handle_alert=None)
        if self.browser.alert_present:
            self.browser.handle_alert(prompt=self.ALERT_PROMPT)
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
                self.appliance.server.sid
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

    title_template = 'Diagnostics Server "{name} [{sid}]"{current}'

    def form_expected_title(self, name, sid, current):
        return self.title_template.format(name=name, sid=sid, current=current)

    @property
    def is_displayed(self):
        tree = self.accordions.diagnostics.tree.currently_selected
        # tree is a list with 3 values: Region, Zone and Server, so we are taking the last
        # Server value is like 'Server: EVM [1] (current)',
        # so we are taking the actual name of the server without the 'Server: '
        selected_server = tree[-1].split(': ')[-1]
        if 'current' in selected_server:
            name, sid, current = selected_server.split()
        else:  # no (current) for slave servers
            name, sid = selected_server.split()
            current = None

        try:
            # output 'title_template' is '[[1]]' which is not intended.
            # stripping square brackets to get the correct output
            sid = sid.strip('[]')
        except ValueError:
            pass

        return (
            self.in_server_collect_logs and
            # compare with the selection in accordion as it can be a slave server
            self.title.text == self.form_expected_title(
                name=name, sid=sid, current='' if current is None else ' (current)')
        )

    @property
    def in_server_collect_logs(self):
        return (
            self.collectlogs.is_displayed and
            self.collectlogs.is_active()
        )


class ServerCollectLogsSlaveView(ServerCollectLogsView):
    @property
    def is_displayed(self):
        # select the first slave server (there's only one slave server in the tests,
        # but appliance.server.slave_servers returns a list)
        try:
            slave_server = self.context['object'].appliance.server.slave_servers[0]
        except IndexError:
            return False  # no slave servers - no ServerCollectLogsSlaveView
        return (
            self.in_server_collect_logs and
            self.title.text == self.form_expected_title(name=slave_server.name,
                                                        sid=slave_server.sid,
                                                        current='')
        )


class ServerCollectLogsMasterView(ServerCollectLogsView):
    @property
    def is_displayed(self):
        master_server = self.context['object'].appliance.server
        return (
            self.in_server_collect_logs and
            self.title.text == self.form_expected_title(name=master_server.name,
                                                        sid=master_server.sid,
                                                        current=' (current)')
        )


class CollectLogsBasicEntities(View):
    fill_strategy = WaitFillViewStrategy("5s")
    depot_name = Input(name='depot_name')
    uri = Input(name='uri')


class CollectLogsCredsEntities(View):
    fill_strategy = WaitFillViewStrategy("5s")
    username = Input(name='log_userid')
    # TODO implement fill method (fill_strategy) to click 'change stored password' when updating
    password = Input(name='log_password')
    confirm_password = Input(name='log_verify')
    validate_button = Button('Validate')


class ServerCollectLogsEditView(ServerCollectLogsView):
    fill_strategy = WaitFillViewStrategy("5s")
    edit_form_title = Text('//form[@id="form_div"]/h3')
    depot_type = BootstrapSelect(id='log_protocol')
    depot_info = View.nested(CollectLogsBasicEntities)
    depot_creds = View.nested(CollectLogsCredsEntities)

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (self.in_server_collect_logs and
                self.depot_type.is_displayed and
                ('Editing Log Depot Settings for Server' in self.edit_form_title.text or
                 'Editing Log Depot Settings for Zone' in self.edit_form_title.text)
                )


class ServerCollectLog(CollectLogsBase):
    """ Represents Server Collect Log settings """
    edit_view = ServerCollectLogsEditView
    main_view = ServerCollectLogsView

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
                self.context['object'].appliance.default_zone.description))


class ZoneCollectLog(CollectLogsBase):
    """ Represents Zone Collect Log settings """
    edit_view = ServerCollectLogsEditView
    main_view = ZoneDiagnosticsCollectLogsView

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

    def step(self, *args, **kwargs):
        self.prerequisite_view.summary.select()


@navigator.register(ServerCollectLog, "DiagnosticsCollectLogs")
class DiagnosticsCollectLogs(CFMENavigateStep):
    VIEW = ServerCollectLogsMasterView
    prerequisite = NavigateToAttribute('appliance.server', 'Diagnostics')

    def step(self, *args, **kwargs):
        # navigate to the master server
        self.prerequisite_view.accordions.diagnostics.tree.click_path(
            self.appliance.server_region_string(),
            "Zone: {} (current)".format(self.appliance.server.zone.description),
            "Server: {} [{}] (current)".format(self.appliance.server.name,
                                self.appliance.server.sid))
        self.prerequisite_view.collectlogs.select()


@navigator.register(ServerCollectLog, "DiagnosticsCollectLogsSlave")
class DiagnosticsCollectLogsSlave(CFMENavigateStep):
    VIEW = ServerCollectLogsSlaveView
    prerequisite = NavigateToAttribute('appliance.server', 'Diagnostics')

    def step(self, *args, **kwargs):
        # navigate to the slave server
        slave_server = self.appliance.server.slave_servers[0]
        self.prerequisite_view.accordions.diagnostics.tree.click_path(
            self.appliance.server_region_string(),
            "Zone: {} (current)".format(self.appliance.server.zone.description),
            "Server: {} [{}]".format(slave_server.name, int(slave_server.sid)))
        self.prerequisite_view.collectlogs.select()


@navigator.register(ServerCollectLog, "DiagnosticsCollectLogsEdit")
@navigator.register(ZoneCollectLog, "DiagnosticsCollectLogsEdit")
class DiagnosticsCollectLogsEdit(CFMENavigateStep):
    VIEW = ServerCollectLogsEditView
    prerequisite = NavigateToSibling('DiagnosticsCollectLogs')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.edit.click()


@navigator.register(ServerCollectLog, "DiagnosticsCollectLogsEditSlave")
class DiagnosticsCollectLogsEditSlave(CFMENavigateStep):
    VIEW = ServerCollectLogsEditView
    prerequisite = NavigateToSibling('DiagnosticsCollectLogsSlave')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.edit.click()


@navigator.register(ZoneCollectLog, 'DiagnosticsCollectLogs')
class ZoneDiagnosticsCollectLogs(CFMENavigateStep):
    VIEW = ZoneDiagnosticsCollectLogsView
    prerequisite = NavigateToAttribute('appliance.server.zone', 'Diagnostics')

    def step(self, *args, **kwargs):
        self.prerequisite_view.collectlogs.select()
