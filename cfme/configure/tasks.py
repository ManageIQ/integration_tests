#!/usr/bin/env python2
# -*- coding: utf-8 -*-

""" Module dealing with Configure/Tasks section.

Todo: Finish the rest of the things.
"""

import cfme.fixtures.pytest_selenium as browser
import cfme.web_ui.tabstrip as tabs
from cfme.web_ui import Form, Region, Table, fill, paginator
from cfme.web_ui.menu import nav
from utils.timeutil import parsetime
from utils.wait import wait_for, TimedOutError


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
        default="//*[@id='buttons_off']/li[3]/a/img",
        apply="//*[@id='buttons_on']/li[1]/a/img",
        reset="//*[@id='buttons_on']/li[2]/a/img"
    )
)

filter_form = Form(
    fields=[
        ("zone", "//select[@id='chosen_zone']"),
        ("user", "//select[@id='user_choice']"),
        ("time_period", "//select[@id='time_period']"),
        ("task_status_queued", "//input[@id='queued']"),
        ("task_status_running", "//input[@id='running']"),
        ("task_status_ok", "//input[@id='ok']"),
        ("task_status_error", "//input[@id='error']"),
        ("task_status_warn", "//input[@id='warn']"),
        ("task_state", "//select[@id='state_choice']"),
    ]
)

tasks_table = Table('//div[@id="records_div"]/table[@class="style3"]')


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
        wait_for(lambda: browser.is_displayed(buttons.apply), num_sec=5)
        browser.click(buttons.apply)
    except TimedOutError:
        pass


def _get_tasks(location, **filter_kwargs):
    """ Generic function to return contents of the tasks table

    Args:
        location: Location for :py:module:`ui_navigate` where to get the data.
        **filter_kwargs: See :py:meth:`_filter`
    Returns: List of dicts.
    """
    browser.force_navigate(location)
    if any([filter_kwargs[key] is not None for key in filter_kwargs.keys()]):
        _filter(**filter_kwargs)
    tasks = []

    if tasks_table.is_displayed:
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
                browser.click(paginator.next())
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
