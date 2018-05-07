# -*- coding: utf-8 -*-

""" Module dealing with Configure/Tasks section.
"""
import attr

from navmazing import NavigateToAttribute
from widgetastic.exceptions import RowNotFound
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View
from widgetastic_manageiq import BootstrapSelect, Button, CheckboxSelect, Table
from widgetastic_patternfly import Dropdown, Tab

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError


class TasksView(BaseLoggedInPage):
    # Toolbar
    delete = Dropdown('Delete Tasks')  # dropdown just has icon, use element title
    reload = Button(title=VersionPick({Version.lowest(): 'Reload the current display',
                                       '5.9': 'Refresh this page'}))

    @View.nested
    class tabs(View):  # noqa
        # Extra Toolbar
        # Only on 'All' type tabs, but for access it doesn't make sense to access the tab for a
        # toolbar button
        cancel = Button(title='Cancel the selected task')

        # Form Buttons
        apply = Button('Apply')
        reset = Button('Reset')
        default = Button('Default')

        # Filters
        zone = BootstrapSelect(id='chosen_zone')
        period = BootstrapSelect(id='time_period')
        user = BootstrapSelect(id='user_choice')
        # This checkbox search_root captures all the filter options
        # It will break for status if/when there is second checkbox selection field added
        # It's the lowest level div with an id that captures the status checkboxes
        status = CheckboxSelect(search_root='tasks_options_div')
        state = BootstrapSelect(id='state_choice')
        table = Table('//div[@id="gtl_div"]//table')

        @View.nested
        class mytasks(Tab):  # noqa
            TAB_NAME = VersionPick({Version.lowest(): 'My VM and Container Analysis Tasks',
                                    '5.9': 'My Tasks'})

        @View.nested
        class myothertasks(Tab):  # noqa
            TAB_NAME = VersionPick({'5.9': 'My Tasks',
                                    Version.lowest(): 'My Other UI Tasks'})

        @View.nested
        class alltasks(Tab):  # noqa
            TAB_NAME = VersionPick({'5.9': 'All Tasks',
                                    Version.lowest(): "All VM and Container Analysis Tasks"})

        @View.nested
        class allothertasks(Tab):  # noqa
            TAB_NAME = "All Other Tasks"

    @property
    def is_displayed(self):
        return (
            self.tabs.mytasks.is_displayed and
            self.tabs.myothertasks.is_displayed and
            self.tabs.alltasks.is_displayed and
            self.tabs.allothertasks.is_displayed)


@attr.s
class Task(BaseEntity):
    """Model of an tasks in cfme.

    Args:
        name: Name of the task.
        user: User who initiated the task.
        server: Cfme server.
        tab: Tab where current task located.

    """
    OK = 'ok'
    ERROR = 'error'
    IN_PROGRESS = 'in_progress'

    name = attr.ib()
    user = attr.ib(default='admin')
    server = attr.ib(default='EVM')    # >= 5.9 only
    tab = attr.ib(default='MyTasks')

    def _is_row_present(self, row_name):
        view = navigate_to(self.parent, self.parent.tab)
        for row in view.tabs.table.rows():
            if row_name in row.task_name.text:
                return True
        return False

    @property
    def _row(self):
        view = navigate_to(self.parent, self.parent.tab)
        wait_for(
            lambda: self._is_row_present(self.name), delay=5, timeout='2m',
            fail_func=view.reload.click)
        row = view.tabs.table.row(task_name=self.name)
        return row

    @property
    def status(self):
        # status column doen't have text id
        if hasattr(self, '_status'):
            return self._status
        col = self._row[1]
        if col.browser.is_displayed('i[@class="pficon pficon-ok"]', parent=col):
            return self.OK
        elif col.browser.is_displayed('i[@class="pficon pficon-error-circle-o"]', parent=col):
            return self.ERROR
        else:
            return self.IN_PROGRESS

    @property
    def state(self):
        return getattr(self, "_state", self._row.state.text)

    @property
    def updated(self):
        return getattr(self, "_updated", self._row.updated.text)

    @property
    def started(self):
        return getattr(self, "_started", self._row.started.text)

    @property
    def queued(self):
        if self.appliance.version >= '5.9':
            return getattr(self, "_queued", self._row.queued.text)
        return None

    @property
    def message(self):
        return getattr(self, "_message", self._row.message.text)

    @property
    def exists(self):
        try:
            self._row
            return True
        except RowNotFound:
            return False

    @property
    def is_successfully_finished(self):
        message = self.message.lower()
        if self.status == self.ERROR:
            if 'timed out' in message:
                raise TimedOutError("Task {} timed out: {}".format(self.name, message))
            else:
                raise Exception("Task {} error: {}".format(self.name, message))

        if self.state.lower() == 'finished' and self.status == self.OK:
            self._status = self.status
            self._state = self.state
            self._updated = self.updated
            self._started = self.started
            if self.appliance.version >= '5.9':
                self._queued = self.queued
            self._message = self.message
            return True
        return False

    def wait_for_finished(self, delay=5, timeout='10m'):
        view = navigate_to(self.parent, self.parent.tab)
        wait_for(
            lambda: self.is_successfully_finished, delay=delay, timeout=timeout,
            fail_func=view.reload.click)


@attr.s
class TaskCollection(BaseCollection):
    """Collection object for :py:class:`cfme.configure.tasks.Task`."""
    ENTITY = Task
    tab = attr.ib(default='MyTasks')

    def switch_tab(self, tab):
        self.tab = tab
        return self

    def set_filter(self, values, cancel=False):
        view = navigate_to(self, self.tab)
        view.fill(values)
        if cancel:
            view.reset.click()
        view.apply.click()

    def set_default_filter(self):
        view = navigate_to(self, self.tab)
        view.default.click()

    def find(self, name):
        tasks = self.all()
        for task in tasks:
            return task if task.name == name else None

    def all(self):
        view = navigate_to(self, self.tab)
        tasks = [self.instantiate(name=row.name.text, tab=self.tab) for row in
                 view.tabs.table.rows()]
        return tasks

    def delete(self, *tasks):
        view = navigate_to(self, self.tab)
        for row in view.tabs.table.rows():
            if row.name in tasks:
                row.check()
        view.delete.item_select('Delete', handle_alert=True)

    def delete_all(self):
        """Deletes all currently visible on page"""
        view = navigate_to(self, self.tab)
        view.delete.item_select('Delete All', handle_alert=True)

    def is_finished(self, *tasks):
        view = navigate_to(self, self.tab)
        for row in view.tabs.table.rows:
            if row.name in tasks and row.state.lower() != "finished":
                return False
        return True

    def is_successfully_finished(self, silent_failure=False, *tasks):
        view = navigate_to(self, self.tab)
        rows = []
        for task in tasks:
            rows.append(view.tabs.table.rows(task_name=task, state='finished'))
        for row in rows:
            message = row.message.text.lower()
            if row[1].browser.is_displayed('i[@class="pficon pficon-error-circle-o"]',
                                           parent=row[1]):
                if silent_failure:
                    logger.warning("Task {} error: {}".format(row.task_name.text, message))
                    return False
                elif 'timed out' in message:
                    raise TimedOutError("Task {} timed out: {}".format(row.task_name.text, message))
                else:
                    Exception("Task {} error: {}".format(row.task_name.text, message))
        return True

    def wait_for_finished(self, delay=5, timeout='5m', *tasks):
        view = navigate_to(self.parent, self.tab)
        wait_for(
            lambda: self.is_finished(tasks), delay=delay, timeout=timeout,
            fail_func=view.reload.click)


@navigator.register(TaskCollection, 'MyTasks')
class MyTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.mytasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.mytasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(TaskCollection, 'MyOtherTasks')
class MyOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.myothertasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.myothertasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(TaskCollection, 'AllTasks')
class AllTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.alltasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.alltasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(TaskCollection, 'AllOtherTasks')
class AllOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.allothertasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.allothertasks
        return tasks.is_displayed and tasks.is_active()
