# -*- coding: utf-8 -*-
import pytest
from cfme.fixtures import pytest_selenium as sel
from utils import testgen
from utils.version import current_version
from cfme.web_ui import toolbar as tb, tabstrip as tabs
from cfme.containers import image
from utils.wait import wait_for, TimedOutError
from cfme.configure import tasks


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


def test_image_analysis_finished():
    # CMP-10064
    image.run_smart_state_analysis()
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
