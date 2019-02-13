# -*- coding: utf-8 -*-
import pytest

from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for


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


@pytest.mark.manual
@pytest.mark.tier(0)
def test_set_memory_threshold_in_ui():
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
            3. Set memory threshold of "Generic Workers" to a value above 1 GB
            4. Hit save
            5. Set the memory threshold of "Event Monitor" to a value above 1 GB
            6. Hit save
        expectedResults:
            1.
            2.
            3.
            4. the change should be reflected in the dropdown
            5.
            6. same as 4.
    """
    pass
