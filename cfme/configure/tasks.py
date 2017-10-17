# -*- coding: utf-8 -*-

""" Module dealing with Configure/Tasks section.
"""
from navmazing import NavigateToAttribute
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View
from widgetastic_manageiq import BootstrapSelect, Button, CheckboxSelect, Table
from widgetastic_patternfly import Dropdown, Tab, FlashMessages

from cfme import web_ui as ui
from cfme.base.login import BaseLoggedInPage
from cfme.web_ui import toolbar as tb
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Form, Region, CheckboxTable, fill
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError

buttons = Region(
    locators={
        'default': '//*[@id="buttons_off"]/a',
        'apply': '//*[@id="buttons_on"]/a[1]',
        'reset': '//*[@id="buttons_on"]/a[2]'
    }
)

filter_form = Form(
    fields=[
        ("zone", ui.Select("//select[@id='chosen_zone']")),
        ("user", ui.Select("//select[@id='user_choice']")),
        ("time_period", ui.Select("//select[@id='time_period']")),
        ("task_status_queued", ui.Input('queued')),
        ("task_status_running", ui.Input('running')),
        ("task_status_ok", ui.Input('ok')),
        ("task_status_error", ui.Input('error')),
        ("task_status_warn", ui.Input('warn')),
        ("task_state", ui.Select("//select[@id='state_choice']")),
    ]
)

table_loc = '//div[@id="records_div"]/table'

tasks_table = CheckboxTable(
    table_locator='//div[@id="records_div"]/table[thead]',
    header_checkbox_locator="//div[@id='records_div']//input[@id='masterToggle']"
)


# TODO move these into Task class
def _filter(
        zone=None,
        user=None,
        time_period=None,
        task_status_queued=None,
        task_status_running=None,
        task_status_ok=None,
        task_status_error=None,
        task_status_warn=None,
        task_state=None):
    """ Does filtering of the results in table. Needs to be on the correct page before called.

    If there was no change in the form and the apply button does not appear, nothing happens.

    Args:
        zone: Value for 'Zone' select
        user: Value for 'User' select
        time_period: Value for 'Time period' select.
        task_status_*: :py:class:`bool` values for checkboxes
        task_state: Value for 'Task State' select.
    """
    fill(filter_form, locals())
    try:
        wait_for(lambda: sel.is_displayed(buttons.apply), num_sec=5)
        sel.click(buttons.apply)
    except TimedOutError:
        pass


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


def wait_analysis_finished(task_name, task_type, delay=5, timeout='5M'):
    """ Wait until analysis is finished (or timeout exceeded)"""
    wait_for(lambda: is_analysis_finished(task_name, task_type),
             delay=delay, timeout=timeout, fail_func=tb.refresh)


class TasksView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')
    # Toolbar
    delete = Dropdown('Delete Tasks')  # dropdown just has icon, use element title
    reload = Button(title='Reload the current display')

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
            TAB_NAME = "My VM and Container Analysis Tasks"
            table = Table(table_loc)

        @View.nested
        class myothertasks(Tab):  # noqa
            TAB_NAME = VersionPick({'5.9': 'My Tasks', Version.lowest(): 'My Other UI Tasks'})
            table = Table(table_loc)

        @View.nested
        class alltasks(Tab):  # noqa
            TAB_NAME = "All VM and Container Analysis Tasks"
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
