# -*- coding: utf-8 -*-

import pytest

from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.nondestructive
@pytest.mark.meta(blockers=[BZ(1531524, forced_streams=["5.9", "upstream"])])
def test_restart_workers(appliance):
    """
    Polarion:
        assignee: mmojzis
        caseimportance: low
        initialEstimate: None
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
