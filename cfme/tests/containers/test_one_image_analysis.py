# -*- coding: utf-8 -*-

""" This module verifies the SSA scan
    On the Images page ---> put a checkmark next to the image
    Click on Configuration ---> Perform SmartState Analysis
    Verify the relevant notification is displayed
    Settings ---> Tasks ---> All VM and Container Analysis Tasks
    Verify the image is being scanned
    Wait for the scan to finish ---> Delete All
"""
import pytest
from cfme.fixtures import pytest_selenium as sel
from utils import testgen
from utils.version import current_version
from cfme.web_ui import flash, toolbar as tb, tabstrip as tabs
from cfme.containers import image
from utils.wait import wait_for, TimedOutError
from cfme.configure import tasks

#  CMP-10064
pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


def test_image_analysis_finished():
    sel.force_navigate('containers_images')
    m = 'Analysis successfully initiated'
    sel.check(image.checkbox)
    tb.select(
        'Configuration',
        'Perform SmartState Analysis',
        invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_contain(m)

    is_task_finished()


def is_task_finished():
    tab_name = "All VM and Container Analysis Tasks"
    page = sel.force_navigate('tasks_all_vm')
    task_name = "Container image analysis"
    expected_status = "finished"
    if not sel.is_displayed(
            tasks.tasks_table) or not tabs.is_tab_selected(tab_name):
        sel.force_navigate(page)

    el = tasks.tasks_table.find_row_by_cells({
        'task_name': task_name,
        'state': expected_status
    })

    if not el:
        try:
            wait_for(is_task_finished, delay=20, timeout="5m",
                     fail_func=lambda: tb.select('Reload'))
        except TimedOutError:
            pytest.fail("Analysis has not completed")

    if el:
        tb.select('Delete Tasks', 'Delete All', invokes_alert=True)
        sel.handle_alert(cancel=False)

        return el
