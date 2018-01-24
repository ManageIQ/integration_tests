# -*- coding: utf-8 -*-

""" Module dealing with Configure/Tasks section.
"""
import re
from navmazing import NavigateToAttribute
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown, Tab

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import TaskFailedException
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError
from widgetastic_manageiq import BootstrapSelect, Button, CheckboxSelect, Table


table_loc = '//div[@id="gtl_div"]//table'

TABS_DATA_PER_PROVIDER = {
    'container': {
        'tab': 'AllTasks',
        'task': '{}',
        'state': 'finished'
    },
    'vm': {
        'tab': 'AllTasks',
        'task': 'Scan from Vm {}',
        'state': 'finished'
    },
    'host': {
        'tab': 'MyOtherTasks',
        'task': "SmartState Analysis for '{}'",
        'state': 'Finished'
    },
    'datastore': {
        'tab': 'MyOtherTasks',
        'task': 'SmartState Analysis for \[{}\]',
        'state': "Finished"
    },
    'cluster': {
        'tab': 'MyOtherTasks',
        'task': 'SmartState Analysis for \[{}\]',
        'state': "Finished"}
}


def is_vm_analysis_finished(name, **kwargs):
    return is_analysis_finished(name=name, task_type='vm', **kwargs)


def is_host_analysis_finished(name, **kwargs):
    return is_analysis_finished(name=name, task_type='host', **kwargs)


def is_datastore_analysis_finished(name, **kwargs):
    return is_analysis_finished(name=name, task_type='datastore', **kwargs)


def is_cluster_analysis_finished(name, **kwargs):
    return is_analysis_finished(name=name, task_type='cluster', **kwargs)


def delete_all_tasks(destination):
    view = navigate_to(Tasks, destination)
    view.delete.item_select('Delete All', handle_alert=True)


def is_analysis_finished(name, task_type='vm', clear_tasks_after_success=True):
    """ Check if analysis is finished - if not, reload page"""

    return check_tasks_have_no_errors(name, task_type, expected_num_of_tasks=1,
                                      silent_failure=False,
                                      clear_tasks_after_success=clear_tasks_after_success)


def are_all_tasks_match_status(name, expected_num_of_tasks, task_type):
    """ Check if all tasks states are finished - if not, reload page"""

    tabs_data = TABS_DATA_PER_PROVIDER[task_type]
    return all_tasks_match_status(
        destination=tabs_data['tab'],
        task_name=tabs_data['task'].format(name),
        expected_status=tabs_data['state'],
        expected_num_of_tasks=expected_num_of_tasks
    )


def all_tasks_match_status(destination, task_name, expected_status, expected_num_of_tasks):
    """ Check if all tasks with same task name states are finished - if not, reload page"""
    view = navigate_to(Tasks, destination)
    tab_view = getattr(view.tabs, destination.lower())

    # task_name change from str to support also regular expression pattern
    task_name = re.compile(task_name)
    # expected_status change from str to support also regular expression pattern
    expected_status = re.compile(expected_status, re.IGNORECASE)

    try:
        rows = list(tab_view.table.rows(task_name=task_name, state=expected_status))
    except IndexError:
        logger.warn('IndexError exception suppressed when searching for task row, no match found.')
        return False

    # check state = finished for all tasks
    return expected_num_of_tasks == len(rows), len(rows)


def check_tasks_have_no_errors(task_name, task_type, expected_num_of_tasks, silent_failure=False,
                               clear_tasks_after_success=False):
    """ Check if all tasks analysis match state with no errors"""

    tabs_data = TABS_DATA_PER_PROVIDER[task_type]
    destination = tabs_data['tab']
    task_name = tabs_data['task'].format(task_name)
    expected_status = tabs_data['state']

    view = navigate_to(Tasks, destination)
    tab_view = getattr(view.tabs, destination.lower())

    # task_name change from str to support also regular expression pattern
    task_name = re.compile(task_name)
    # expected_status change from str to support also regular expression pattern
    expected_status = re.compile(expected_status, re.IGNORECASE)

    try:
        rows = list(tab_view.table.rows(task_name=task_name, state=expected_status))
    except IndexError:
        logger.warn('IndexError exception suppressed when searching for task row, no match found.')
        return False

    # check state for all tasks
    if expected_num_of_tasks != len(rows):
        logger.warn('There is no match between expected number of tasks "{}",'
                    ' and number of tasks on state "{}'.format(expected_num_of_tasks,
                                                               expected_status))
        return False

    # throw exception if error in message
    for row in rows:
        message = row.message.text.lower()
        for term in ('error', 'timed out', 'failed', 'unable to run openscap'):
            if term in message:
                if silent_failure:
                    logger.warning("Task {} error: {}".format(row.task_name.text, message))
                    return False
                elif term == 'timed out':
                    raise TimedOutError("Task {} timed out: {}".format(row.task_name.text, message))
                else:
                    raise TaskFailedException(task_name=row.task_name.text, message=message)

    if clear_tasks_after_success:
        # Remove all finished tasks so they wouldn't poison other tests
        delete_all_tasks(destination)

    return True


def wait_analysis_finished_multiple_tasks(
        task_name, task_type, expected_num_of_tasks, delay=5, timeout='5M'):
    """ Wait until analysis is finished (or timeout exceeded)"""
    row_completed = []
    # get view for reload button
    view = navigate_to(Tasks, 'AllTasks')

    def tasks_finished(output_rows, task_name, task_type, expected_num_of_tasks):

        is_succeed, num_of_succeed_tasks = are_all_tasks_match_status(
            task_name, expected_num_of_tasks, task_type)
        output_rows.append(num_of_succeed_tasks)
        return is_succeed

    try:
        wait_for(tasks_finished,
                 func_kwargs={'output_rows': row_completed,
                              'task_name': task_name,
                              'task_type': task_type,
                              'expected_num_of_tasks': expected_num_of_tasks},
                 delay=delay,
                 timeout=timeout,
                 fail_func=view.reload.click)
        return row_completed[-1]
    except TimedOutError, e:
        logger.error("Only {}  Tasks out of {}, Finished".format(row_completed[-1],
                                                                 expected_num_of_tasks))
        raise TimedOutError('exception {}'.format(e))


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

        @View.nested
        class mytasks(Tab):  # noqa
            TAB_NAME = VersionPick({Version.lowest(): 'My VM and Container Analysis Tasks',
                                    '5.9': 'My Tasks'})
            table = Table(table_loc)

        @View.nested
        class myothertasks(Tab):  # noqa
            TAB_NAME = VersionPick({'5.9': 'My Tasks',
                                    Version.lowest(): 'My Other UI Tasks'})
            table = Table(table_loc)

        @View.nested
        class alltasks(Tab):  # noqa
            TAB_NAME = VersionPick({'5.9': 'All Tasks',
                                    Version.lowest(): "All VM and Container Analysis Tasks"})
            table = Table(table_loc)

        @View.nested
        class allothertasks(Tab):  # noqa
            TAB_NAME = "All Other Tasks"
            table = Table(table_loc)

    @property
    def is_displayed(self):
        return (
            self.tabs.mytasks.is_displayed and
            self.tabs.myothertasks.is_displayed and
            self.tabs.alltasks.is_displayed and
            self.tabs.allothertasks.is_displayed)


class Tasks(Navigatable):
    pass


@navigator.register(Tasks, 'MyTasks')
class MyTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.mytasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.mytasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(Tasks, 'MyOtherTasks')
class MyOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.myothertasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.myothertasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(Tasks, 'AllTasks')
class AllTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.alltasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.alltasks
        return tasks.is_displayed and tasks.is_active()


@navigator.register(Tasks, 'AllOtherTasks')
class AllOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.allothertasks.select()

    def am_i_here(self):
        tasks = self.view.tabs.allothertasks
        return tasks.is_displayed and tasks.is_active()
