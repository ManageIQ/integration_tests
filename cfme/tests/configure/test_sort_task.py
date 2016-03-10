# -*- coding: utf-8 -*-
import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.configure import tasks


@pytest.mark.sauce
def test_sort_my_vm_tasks():
    sel.force_navigate('tasks_my_vm')
    other_tasks = tasks.all_other_tasks()
    if len(other_tasks) > 1:
        tasks.sort_by_header('Started', 'ascending')


@pytest.mark.sauce
def test_sort_my_other_ui_tasks():
    sel.force_navigate('tasks_my_other_ui')
    other_tasks = tasks.all_other_tasks()
    if len(other_tasks) > 1:
        tasks.sort_by_header('Started', 'ascending')


@pytest.mark.sauce
def test_sort_all_vm_analysis_tasks():
    sel.force_navigate('tasks_all_vm')
    other_tasks = tasks.all_other_tasks()
    if len(other_tasks) > 1:
        tasks.sort_by_header('Started', 'ascending')


@pytest.mark.sauce
def test_sort_all_other_tasks():
    sel.force_navigate('tasks_all_other')
    other_tasks = tasks.all_other_tasks()
    if len(other_tasks) > 1:
        tasks.sort_by_header('Started', 'ascending')
