""" Module dealing with Configure/Tasks section.
"""
import re

import attr
from navmazing import NavigateToAttribute
from widgetastic.exceptions import RowNotFound
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for
from widgetastic_manageiq import BootstrapSelect
from widgetastic_manageiq import Button
from widgetastic_manageiq import CheckboxSelect
from widgetastic_manageiq import Table
from widgetastic_manageiq import WaitTab


class TasksView(BaseLoggedInPage):
    # Toolbar
    delete = Dropdown('Delete Tasks')  # dropdown just has icon, use element title
    reload = Button(title='Refresh this page')

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

        @View.nested
        class mytasks(WaitTab):  # noqa
            TAB_NAME = 'My Tasks'
            table = Table('//div[@id="gtl_div"]//table')

        @View.nested
        class myothertasks(WaitTab):  # noqa
            TAB_NAME = 'My Tasks'
            table = Table('//div[@id="gtl_div"]//table')

        @View.nested
        class alltasks(WaitTab):  # noqa
            TAB_NAME = 'All Tasks'
            table = Table('//div[@id="gtl_div"]//table')

        @View.nested
        class allothertasks(WaitTab):  # noqa
            TAB_NAME = "All Other Tasks"
            table = Table('//div[@id="gtl_div"]//table')

    @property
    def is_displayed(self):
        return (
            self.tabs.mytasks.is_displayed and
            self.tabs.alltasks.is_displayed
        )


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
    tab = attr.ib(default='AllTasks')

    def _is_row_present(self, row_name):
        view = navigate_to(self.parent, self.tab)
        tab_view = getattr(view.tabs, self.tab.lower())
        for row in tab_view.table.rows():
            if row_name in row.task_name.text:
                return True
        return False

    @property
    def _row(self):
        view = navigate_to(self.parent, self.tab)
        tab_view = getattr(view.tabs, self.tab.lower())
        wait_for(
            lambda: self._is_row_present(self.name), delay=5, timeout='15m',
            fail_func=view.reload.click)
        row = tab_view.table.row(task_name=self.name)
        return row

    @property
    def status(self):
        # status column doen't have text id
        col = self._row[1]
        if col.browser.is_displayed('i[@class="pficon pficon-ok"]', parent=col):
            return self.OK
        elif col.browser.is_displayed('i[@class="pficon pficon-error-circle-o"]', parent=col):
            return self.ERROR
        else:
            return self.IN_PROGRESS

    @property
    def state(self):
        return self._row.state.text

    @property
    def updated(self):
        return self._row.updated.text

    @property
    def started(self):
        return self._row.started.text

    @property
    def queued(self):
        return self._row.queued.text

    @property
    def message(self):
        return self._row.message.text

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
                raise TimedOutError(f"Task {self.name} timed out: {message}")
            else:
                raise Exception(f"Task {self.name} error: {message}")

        if self.state.lower() == 'finished' and self.status == self.OK:
            return True
        return False

    def wait_for_finished(self, delay=5, timeout='15m'):
        view = navigate_to(self.parent, self.tab)
        wait_for(
            lambda: self.is_successfully_finished, delay=delay, timeout=timeout,
            fail_func=view.reload.click)


@attr.s
class TasksCollection(BaseCollection):
    """Collection object for :py:class:`cfme.configure.tasks.Task`."""
    ENTITY = Task

    DEFAULT_TAB = 'AllTasks'

    @property
    def tab(self):
        return self.filters.get('tab') or self.DEFAULT_TAB

    def set_task_filter(self, values, cancel=False):
        view = navigate_to(self, self.tab)
        view.fill(values)
        if cancel:
            view.reset.click()
        view.apply.click()

    def set_default_task_filter(self):
        view = navigate_to(self, self.tab)
        view.default.click()

    def find(self, name):
        tasks = self.all()
        for task in tasks:
            return task if task.name == name else None

    def all(self):
        view = navigate_to(self, self.tab)
        tab_view = getattr(view.tabs, self.tab.lower())
        tasks = [self.instantiate(name=row.name.text, tab=self.tab) for row in
                 tab_view.table.rows()]
        return tasks

    def delete(self, *tasks):
        view = navigate_to(self, self.tab)
        tab_view = getattr(view.tabs, self.tab.lower())
        for row in tab_view.table.rows():
            if row.name in tasks:
                row.check()
        view.delete.item_select('Delete', handle_alert=True)

    def delete_all(self):
        """Deletes all currently visible on page"""
        view = navigate_to(self, self.tab)
        view.delete.item_select('Delete All', handle_alert=True)

    def is_finished(self, *tasks):
        view = navigate_to(self, self.tab)
        tab_view = getattr(view.tabs, self.tab.lower())
        for row in tab_view.table.rows():
            if row.task_name.text in tasks and row.state.text.lower() != "finished":
                return False
        return True

    def is_successfully_finished(self, silent_failure=False, *tasks):
        view = navigate_to(self, self.tab)
        tab_view = getattr(view.tabs, self.tab.lower())
        rows = []
        # expected_status support also regular expression pattern
        expected_status = re.compile('finished', re.IGNORECASE)
        for task in tasks:
            try:
                rows.append(list(tab_view.table.rows(task_name=task, state=expected_status)).pop())
            except IndexError:
                logger.warning('IndexError exception suppressed when searching for task row,'
                            ' no match found.')
                return False
        for row in rows:
            message = row.message.text.lower()
            if row[1].browser.is_displayed('i[@class="pficon pficon-error-circle-o"]',
                                           parent=row[1]):
                if silent_failure:
                    logger.warning(f"Task {row.task_name.text} error: {message}")
                    return False
                elif 'timed out' in message:
                    raise TimedOutError(f"Task {row.task_name.text} timed out: {message}")
                else:
                    Exception(f"Task {row.task_name.text} error: {message}")
        return True

    def wait_for_finished(self, delay=5, timeout='5m', *tasks):
        view = navigate_to(self, self.tab)
        wait_for(
            lambda: self.is_finished(*tasks), delay=delay, timeout=timeout,
            fail_func=view.reload.click)


@navigator.register(TasksCollection, 'MyTasks')
class MyTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.mytasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.mytasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(TasksCollection, 'MyOtherTasks')
class MyOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.myothertasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.myothertasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(TasksCollection, 'AllTasks')
class AllTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.alltasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.alltasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(TasksCollection, 'AllOtherTasks')
class AllOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.allothertasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.allothertasks
        return tasks.is_displayed and tasks.is_active()
