# -*- coding: utf-8 -*-

""" Module dealing with Configure/Tasks section.
"""

from cfme import web_ui as ui
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.tabstrip as tabs
from cfme.web_ui import Form, Region, CheckboxTable, fill, paginator, toolbar
from cfme.web_ui.menu import nav
from utils.timeutil import parsetime
from utils.wait import wait_for, TimedOutError
from utils.version import LOWEST


nav.add_branch("tasks",
    dict(
        tasks_my_vm=lambda _: tabs.select_tab("My VM Analysis Tasks"),
        tasks_my_other_ui=lambda _: tabs.select_tab("My Other UI Tasks"),
        tasks_all_vm=lambda _: tabs.select_tab("All VM Analysis Tasks"),
        tasks_all_other=lambda _: tabs.select_tab("All Other Tasks"),
    )
)

buttons = Region(
    locators=dict(
        default={LOWEST: "//*[@id='buttons_off']/li[3]/a/img",
                 '5.4': "//*[@id='buttons_off']/a"},
        apply={LOWEST: "//*[@id='buttons_on']/li[1]/a/img",
               '5.4': "//*[@id='buttons_on']/a[1]"},
        reset={LOWEST: "//*[@id='buttons_on']/li[2]/a/img",
               '5.4': "//*[@id='buttons_on']/a[2]"}
    )
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
    table_locator={
        LOWEST: '//div[@id="records_div"]/table[@class="style3"]',
        "5.4": '//div[@id="records_div"]/table[thead]'},
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


def _get_tasks(location, **filter_kwargs):
    """ Generic function to return contents of the tasks table

    Args:
        location: Location for :py:module:`ui_navigate` where to get the data.
        **filter_kwargs: See :py:meth:`_filter`
    Returns: List of dicts.
    """
    sel.force_navigate(location)
    if any([filter_kwargs[key] is not None for key in filter_kwargs.keys()]):
        _filter(**filter_kwargs)
    tasks = []

    if sel.is_displayed(tasks_table):
        have_next_page = True
        while have_next_page:
            for row in tasks_table.rows():
                tasks.append(
                    dict(
                        updated=parsetime.from_american_with_utc(
                            row.updated.text.encode('utf-8').strip()
                        ),
                        started=parsetime.from_american_with_utc(
                            row.started.text.encode('utf-8').strip()
                        ),
                        state=row.state.text.encode('utf-8').strip(),
                        message=row.message.text.encode('utf-8').strip(),
                        task_name=row.task_name.text.encode('utf-8').strip(),
                        user=row.user.text.encode('utf-8').strip()
                    )
                )
            if int(paginator.rec_end()) < int(paginator.rec_total()):
                sel.click(paginator.next())
            else:
                have_next_page = False
    return tasks


def my_vm_analysis_tasks(**filter_kwargs):
    """ Returns all tasks in the table for 'My VM Analysis Tasks'

    Args:
        **filter_kwargs: See :py:meth:`_filter`
    Returns: List of dicts.
    """
    return _get_tasks("tasks_my_vm", **filter_kwargs)


def my_other_ui_tasks(**filter_kwargs):
    """ Returns all tasks in the table for 'My Other UI Tasks'

    Args:
        **filter_kwargs: See :py:meth:`_filter`
    Returns: List of dicts.
    """
    return _get_tasks("tasks_my_other_ui", **filter_kwargs)


def all_vm_analysis_tasks(**filter_kwargs):
    """ Returns all tasks in the table for 'All VM Analysis Tasks'

    Args:
        **filter_kwargs: See :py:meth:`_filter`
    Returns: List of dicts.
    """
    return _get_tasks("tasks_all_vm", **filter_kwargs)


def all_other_tasks(**filter_kwargs):
    """ Returns all tasks in the table for 'All Other Tasks'

    Args:
        **filter_kwargs: See :py:meth:`_filter`
    Returns: List of dicts.
    """
    return _get_tasks("tasks_all_other", **filter_kwargs)


def is_vm_analysis_finished(name, **kwargs):
    return is_analysis_finished(name=name, task_type='vm', **kwargs)


def is_host_analysis_finished(name, **kwargs):
    return is_analysis_finished(name=name, task_type='host', **kwargs)


def is_datastore_analysis_finished(name, **kwargs):
    return is_analysis_finished(name=name, task_type='datastore', **kwargs)


def is_task_finished(tab, page, task_name, expected_status, clear_tasks_after_success=True):
    el = None
    try:
        if not sel.is_displayed(tasks_table) or not tabs.is_tab_selected(tab):
            sel.force_navigate(page)
        el = tasks_table.find_row_by_cells({
            'task_name': task_name,
            'state': expected_status
        })
        if el is None:
            return False
    except Exception:
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
            'tab': 'All VM Analysis Tasks',
            'page': 'tasks_all_vm',
            'task': 'Scan from Vm {}',
            'state': 'finished'
        },
        'host': {
            'tab': 'My Other UI Tasks',
            'page': 'tasks_my_other_ui',
            'task': 'SmartState Analysis for {}',
            'state': 'Finished'
        },
        'datastore': {
            'tab': 'My Other UI Tasks',
            'page': 'tasks_my_other_ui',
            'task': 'SmartState Analysis for [{}]',
            'state': "Finished"}
    }[task_type]

    return is_task_finished(tab=tabs_data['tab'],
                            page=tabs_data['page'],
                            task_name=tabs_data['task'].format(name),
                            expected_status=tabs_data['state'],
                            clear_tasks_after_success=clear_tasks_after_success)
