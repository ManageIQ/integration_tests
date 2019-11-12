from collections import namedtuple

import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.rhel_testing]

Dropdown = namedtuple('Dropdown', 'dropdown id')

DROPDOWNS = [
    Dropdown('generic_worker_threshold', 'generic'),
    Dropdown('cu_data_collector_worker_threshold', 'cu_data_coll'),
    Dropdown('event_monitor_worker_threshold', 'event_monitor'),
    Dropdown('connection_broker_worker_threshold', 'conn_broker'),
    Dropdown('reporting_worker_threshold', 'reporting'),
    Dropdown('web_service_worker_threshold', 'web_service'),
    Dropdown('priority_worker_threshold', 'priority'),
    Dropdown('cu_data_processor_worker_threshold', 'cu_data_proc'),
    Dropdown('refresh_worker_threshold', 'refresh'),
    Dropdown('vm_analysis_collectors_worker_threshold', 'vm_analysis')
]


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_restart_workers(appliance):
    """
    Polarion:
        assignee: tpapaioa
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


@pytest.mark.tier(2)
@pytest.mark.parametrize("dropdown", [x.dropdown for x in DROPDOWNS], ids=[x.id for x in DROPDOWNS])
def test_set_memory_threshold_in_ui(appliance, dropdown):
    """
    Bugzilla:
        1656873

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/6h
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
    change = "1.1 GB"
    if before == change:
        change = "1.2 GB"
    mem_threshold.select_by_visible_text(change)
    view.workers.save.click()
    view.wait_displayed()
    after = mem_threshold.selected_option

    assert before != after
    assert after == change

    # reset the mem threshold after the test
    view.workers.reset.click()
