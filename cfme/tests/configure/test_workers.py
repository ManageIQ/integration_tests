from collections import namedtuple
from copy import deepcopy

import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.rhel_testing]

Worker = namedtuple('Worker', 'dropdown id advanced')

WORKERS = [
    Worker('generic_worker_threshold', 'generic', 'generic_worker'),
    Worker('cu_data_collector_worker_threshold', 'cu_data_coll', 'ems_metrics_collector_worker'),
    Worker('event_monitor_worker_threshold', 'event_monitor', 'event_catcher'),
    Worker('connection_broker_worker_threshold', 'conn_broker', 'vim_broker_worker'),
    Worker('reporting_worker_threshold', 'reporting', 'reporting_worker'),
    Worker('web_service_worker_threshold', 'web_service', 'web_service_worker'),
    Worker('priority_worker_threshold', 'priority', 'priority_worker'),
    Worker('cu_data_processor_worker_threshold', 'cu_data_proc', 'ems_metrics_processor_worker'),
    Worker('refresh_worker_threshold', 'refresh', 'ems_refresh_worker'),
    Worker('vm_analysis_collectors_worker_threshold', 'vm_analysis', 'smart_proxy_worker')
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


@pytest.fixture(scope="module")
def _workers_default_settings(appliance):
    a = deepcopy(appliance.server.advanced_settings['workers'])
    return a


def set_memory_threshold_in_ui(appliance, worker, new_threshold, new_threshold_if_taken):
    view = navigate_to(appliance.server, 'Workers')
    view.browser.refresh()
    mem_threshold = getattr(view.workers, worker.dropdown)
    before = mem_threshold.selected_option
    if before[:3] == new_threshold[:3]:
        new_threshold = new_threshold_if_taken
    mem_threshold.select_by_visible_text(new_threshold.replace('.gigabytes', ' GB'))
    view.workers.save.click()
    view.wait_displayed()
    return before, new_threshold


def set_memory_threshold_in_advanced_settings(appliance, worker, new_threshold,
                                              new_threshold_if_taken):
    worker_base = appliance.server.advanced_settings['workers']['worker_base']
    workerro = worker_base.get(worker.advanced, None)
    queue_worker = not workerro
    if not workerro:
        workerro = worker_base['queue_worker_base'][worker.advanced]
        worker_base = worker_base['queue_worker_base']
    before = workerro.get('memory_threshold', worker_base['defaults']['memory_threshold'])
    if before[:3] == new_threshold[:3]:
        new_threshold = new_threshold_if_taken
    change_defaults = worker.advanced in ['ems_refresh_worker', 'ems_metrics_collector_worker']
    if not change_defaults:
        worker_base[worker.advanced]['memory_threshold'] = new_threshold
    else:
        worker_base[worker.advanced]['defaults']['memory_threshold'] = new_threshold
    if queue_worker:
        worker_base = {'queue_worker_base': worker_base}
    patch = {
        'workers': {
            'worker_base': worker_base
        }
    }
    # set worker threshold
    appliance.server.update_advanced_settings(patch)
    return before, new_threshold


CHECK_UI = "ui"
CHECK_ADVANCED_SETTINGS = "advanced"


@test_requirements.settings
@pytest.mark.tier(2)
@pytest.mark.parametrize("set_memory_threshold",
                         [set_memory_threshold_in_ui, set_memory_threshold_in_advanced_settings],
                         ids=["in_UI", "in_advanced_setting"])
@pytest.mark.parametrize("threshold_change", ["1.1.gigabytes"])
@pytest.mark.parametrize("worker", WORKERS, ids=[x.id for x in WORKERS])
@pytest.mark.meta(blocker=[1787350], coverage=[1658373, 1715633])
def test_set_memory_threshold(appliance, worker, set_memory_threshold, threshold_change,
                              _workers_default_settings):
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
    other = {
        "1.1.gigabytes": "1.2.gigabytes",
        "1.2.gigabytes": "1.1.gigabytes"
    }
    before, change = set_memory_threshold(appliance, worker, threshold_change,
                                          other[threshold_change])
    # check UI
    view = navigate_to(appliance.server, 'Workers')
    view.browser.refresh()
    mem_threshold = getattr(view.workers, worker.dropdown)
    after = mem_threshold.selected_option
    assert after.startswith(change.replace(".gigabytes", " GB")), "failed UI check"
    # check advanced settings
    worker_type = worker.advanced
    change_val = float(change.replace('.gigabytes', ''))
    try:
        mem_threshold_real = (appliance.server.advanced_settings['workers']['worker_base']
        ['queue_worker_base'][f'{worker_type}']['memory_threshold'])
    except KeyError:
        mem_threshold_real = (appliance.server.advanced_settings['workers']['worker_base']
        [f'{worker_type}']['memory_threshold'])
    GB = 2 ** 30
    MESSAGE = "memory threshold have changed incorrectly in advanced settings"
    if appliance.version >= "5.11":
        assert mem_threshold_real == f"{change_val}.gigabytes", MESSAGE
    else:
        expected_value = change_val * GB
        # this tests if memory threshold has changed and is approximately correct
        assert abs(mem_threshold_real - expected_value) < expected_value * 0.01, MESSAGE
    # reset settings back to default
    appliance.server.update_advanced_settings(
        {'workers': _workers_default_settings}
    )
