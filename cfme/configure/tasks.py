# -*- coding: utf-8 -*-

""" Module dealing with Configure/Tasks section.
"""
import re
from navmazing import NavigateToAttribute
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View
from widgetastic_manageiq import BootstrapSelect, Button, CheckboxSelect, Table
from widgetastic_patternfly import Dropdown, Tab, FlashMessages

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError

table_loc = '//div[@id="gtl_div"]//table'


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


def is_task_finished(destination, task_name, expected_status, clear_tasks_after_success=True):
    view = navigate_to(Tasks, destination)
    tab_view = getattr(view.tabs, destination.lower())

    # task_name change from str to support also regular expression pattern
    task_name = re.compile(task_name)
    # expected_status change from str to support also regular expression pattern
    expected_status = re.compile(expected_status, re.IGNORECASE)

    try:
        row = tab_view.table.row(task_name=task_name, state=expected_status)
    except IndexError:
        logger.warn('IndexError exception suppressed when searching for task row, no match found.')
        return False

    # throw exception if error in message
    message = row.message.text.lower()
    if 'error' in message:
        raise Exception("Task {} error: {}".format(task_name, message))
    elif 'timed out' in message:
        raise TimedOutError("Task {} timed out: {}".format(task_name, message))
    elif 'failed' in message:
        raise Exception("Task {} has a failure: {}".format(task_name, message))

    if clear_tasks_after_success:
        # Remove all finished tasks so they wouldn't poison other tests
        delete_all_tasks(destination)

    return True


def is_analysis_finished(name, task_type='vm', clear_tasks_after_success=True):
    """ Check if analysis is finished - if not, reload page"""

    tabs_data = {
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
            'task': 'SmartState Analysis for [{}]',
            'state': "Finished"
        },
        'cluster': {
            'tab': 'MyOtherTasks',
            'task': 'SmartState Analysis for [{}]',
            'state': "Finished"}
    }[task_type]
    return is_task_finished(destination=tabs_data['tab'],
                            task_name=tabs_data['task'].format(name),
                            expected_status=tabs_data['state'],
                            clear_tasks_after_success=clear_tasks_after_success)


class TasksView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')
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
        return self.view.tabs.mytasks.is_active()


@navigator.register(Tasks, 'MyOtherTasks')
class MyOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.myothertasks.select()

    def am_i_here(self):
        return self.view.tabs.myothertasks.is_active()


@navigator.register(Tasks, 'AllTasks')
class AllTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.alltasks.select()

    def am_i_here(self):
        return self.view.tabs.alltasks.is_active()


@navigator.register(Tasks, 'AllOtherTasks')
class AllOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.allothertasks.select()

    def am_i_here(self):
        return self.view.tabs.allothertasks.is_active()
