# -*- coding: utf-8 -*-
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for

DROPDOWNS = [
    'generic_worker_threshold',
    'cu_data_collector_worker_threshold',
    'event_monitor_worker_threshold',
    'connection_broker_worker_threshold',
    'reporting_worker_threshold',
    'web_service_worker_threshold',
    'priority_worker_threshold',
    'cu_data_processor_worker_threshold',
    'refresh_worker_threshold',
    'vm_analysis_collectors_worker_threshold'
]

IDS = [
    'generic',
    'cu_data_coll',
    'event_monitor',
    'conn_broker',
    'reporting',
    'web_service',
    'priority',
    'cu_data_proc',
    'refresh',
    'vm_analysis'
]


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.nondestructive
@pytest.mark.meta(blockers=[BZ(1672758)])
def test_restart_workers(appliance):
    """
    Polarion:
        assignee: anikifor
        caseimportance: high
        initialEstimate: 1/4h
        casecomponent: Configuration
    """
    worker = appliance.collections.diagnostic_workers.instantiate(name="Generic Worker")
    pids = worker.reload_worker()
    # Wait for all original workers to be gone
    wait_for(worker.check_workers_finished, func_args=[pids],
             fail_func=worker.parent.reload_workers_page,
             num_sec=1800, delay=10, message="Wait for all original workers to be gone")
    # And now check whether the same number of workers is back online
    wait_for(lambda: len(pids) == len(worker.get_all_worker_pids()),
             fail_func=worker.parent.reload_workers_page, num_sec=1800, delay=10,
             message="Wait for all original workers are back online")


@pytest.mark.tier(0)
@pytest.mark.parametrize("dropdown", DROPDOWNS, ids=IDS)
@pytest.mark.meta(blockers=[BZ(1656873)])
def test_set_memory_threshold_in_ui(appliance, dropdown):
    """
    Bugzillas:
        * 1656873

    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/30h
        testSteps:
            1. Navigate to Configuration
            2. Select the workers tab
            3. Set memory threshold of any dropdown to a value above 1 GB
            4. Hit save
        expectedResults:
            1.
            2.
            3.
            4. the change should be reflected in the dropdown
    """
    view = navigate_to(appliance.server, 'Workers')
    mem_threshold = getattr(view.workers, dropdown)
    before = mem_threshold.selected_option
    mem_threshold.select_by_visible_text("1.1 GB")
    view.workers.save.click()
    view.wait_displayed()
    after = mem_threshold.selected_option

    assert before != after
    assert after == "1.1 GB"

    # reset the mem threshold after the test
    view.workers.reset.click()
