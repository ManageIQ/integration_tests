# -*- coding: utf-8 -*-

""" Module dealing with Configure/Tasks section.
"""

from navmazing import NavigateToAttribute

from cfme import web_ui as ui
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.tabstrip as tabs
from cfme.web_ui import Form, Region, CheckboxTable, fill, toolbar, match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.wait import wait_for, TimedOutError
from cfme.services import requests

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

tasks_table = CheckboxTable(
    table_locator='//div[@id="records_div"]/table[thead]',
    header_checkbox_locator="//div[@id='records_div']//input[@id='masterToggle']"
)


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


def is_task_finished(tab_destination, task_name, expected_status, clear_tasks_after_success=True):
    navigate_to(Tasks, tab_destination)
    el = tasks_table.find_row_by_cells({
        'task_name': task_name,
        'state': expected_status
    })
    if el is None:
        return False

    # throw exception if status is error
    if 'Error' in sel.get_attribute(sel.element('.//td/img', root=el), 'title'):
        raise Exception("Task {} errored".format(task_name))

    if clear_tasks_after_success:
        # Remove all finished tasks so they wouldn't poison other tests
        toolbar.select('Delete Tasks', 'Delete All', invokes_alert=True)
        sel.handle_alert(cancel=False)

    return True


def is_analysis_finished(name, task_type='vm', clear_tasks_after_success=True):
    """ Check if analysis is finished - if not, reload page"""

    tabs_data = {
        'vm': {
            'tab': 'AllVMContainerAnalysis',
            'task': '{}',
            'state': 'finished'
        },
        'host': {
            'tab': 'MyOther',
            'task': "SmartState Analysis for '{}'",
            'state': 'Finished'
        },
        'datastore': {
            'tab': 'MyOther',
            'page': 'tasks_my_other_ui',
            'task': 'SmartState Analysis for [{}]',
            'state': "Finished"
        },
        'cluster': {
            'tab': 'MyOther',
            'page': 'tasks_my_other_ui',
            'task': 'SmartState Analysis for [{}]',
            'state': "Finished"}
    }[task_type]

    return is_task_finished(tab_destination=tabs_data['tab'],
                            task_name=tabs_data['task'].format(name),
                            expected_status=tabs_data['state'],
                            clear_tasks_after_success=clear_tasks_after_success)


def wait_analysis_finished(task_name, task_type, delay=5, timeout='5M'):
    """ Wait until analysis is finished (or timeout exceeded)"""
    wait_for(lambda: is_analysis_finished(task_name, task_type),
             delay=delay, timeout=timeout, fail_func=requests.reload)


class Tasks(Navigatable):
    pass


@navigator.register(Tasks, 'MyVMContainerAnalysis')
class MyVMContainerAnalysis(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    tab_name = 'My VM and Container Analysis Tasks'

    def step(self, *args, **kwargs):
        tabs.select_tab(self.tab_name)

    def am_i_here(self):
        return match_location(controller='miq_task', title='My Tasks') and \
            tabs.is_tab_selected(self.tab_name)


@navigator.register(Tasks, 'MyOther')
class MyOther(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    tab_name = 'My Other UI Tasks'

    def step(self, *args, **kwargs):
        tabs.select_tab(self.tab_name)

    def am_i_here(self):
        return match_location(controller='miq_task', title='My UI Tasks') and \
            tabs.is_tab_selected()


@navigator.register(Tasks, 'AllVMContainerAnalysis')
class AllVMContainerAnalysis(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    tab_name = "All VM and Container Analysis Tasks"

    def step(self, *args, **kwargs):
        tabs.select_tab(self.tab_name)

    def am_i_here(self):
        return match_location(controller='miq_task', title='All Tasks') and \
            tabs.is_tab_selected(self.tab_name)


@navigator.register(Tasks, 'AllOther')
class AllOther(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    tab_name = 'All Other Tasks'

    def step(self, *args, **kwargs):
        tabs.select_tab(self.tab_name)

    def am_i_here(self):
        return match_location(controller='miq_task', title='All UI Tasks') and \
            tabs.is_tab_selected(self.tab_name)
