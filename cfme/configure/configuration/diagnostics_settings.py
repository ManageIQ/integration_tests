import attr

from navmazing import NavigateToAttribute
from widgetastic_patternfly import Button, Dropdown
from widgetastic.widget import View, Table, RowNotFound

from cfme.base.ui import ServerDiagnosticsView
from cfme.modeling.base import BaseEntity, BaseCollection
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


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
            view.workers_table.row(pid=pid_item).click()
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
