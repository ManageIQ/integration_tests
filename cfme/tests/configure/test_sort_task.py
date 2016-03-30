# -*- coding: utf-8 -*-
import pytest
import cfme.infrastructure.virtual_machines as vm

from cfme.fixtures import pytest_selenium as sel
from cfme.configure import tasks
from utils.providers import setup_a_provider


@pytest.fixture(scope="module")
def provider():
    return setup_a_provider(prov_class="infra", prov_type="rhevm")


def test_sort_my_vm_tasks(provider):
    vm_list = vm.get_all_vms()
    vm.perform_smartstate_analysis(vm_list)
    sel.force_navigate('tasks_my_vm')
    other_tasks = tasks.my_vm_analysis_tasks()
    if len(other_tasks) > 1:
        tasks.sort_by_header('Task Name', 'ascending')


def test_sort_my_other_ui_tasks():
    sel.force_navigate('tasks_my_other_ui')
    other_tasks = tasks.my_other_ui_tasks()
    if len(other_tasks) > 1:
        tasks.sort_by_header('Task Name', 'ascending')


def test_sort_all_vm_analysis_tasks(provider):
    sel.force_navigate('tasks_all_vm')
    other_tasks = tasks.all_vm_analysis_tasks()
    if len(other_tasks) > 1:
        tasks.sort_by_header('Task Name', 'ascending')


def test_sort_all_other_tasks():
    sel.force_navigate('tasks_all_other')
    other_tasks = tasks.all_other_tasks()
    if len(other_tasks) > 1:
        tasks.sort_by_header('Task Name', 'ascending')
