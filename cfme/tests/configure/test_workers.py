from collections import namedtuple

import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.rhel_testing]

# paths in advanced settings yaml where to put their memory_threshold
# starting in worker_base and '*' means worker itself
BASE_PATH = ['*']
QUEUE_WORKER_PATH = ['queue_worker_base', '*']
QUEUE_WORKER_DEFAULTS_PATH = QUEUE_WORKER_PATH + ['defaults']

Worker = namedtuple('Worker', 'dropdown id advanced path')

WORKERS = [
    Worker('generic_worker_threshold', 'generic',
           'generic_worker', QUEUE_WORKER_PATH),
    Worker('cu_data_collector_worker_threshold', 'cu_data_coll',
           'ems_metrics_collector_worker', QUEUE_WORKER_DEFAULTS_PATH),
    Worker('event_monitor_worker_threshold', 'event_monitor',
           'event_catcher', BASE_PATH),
    Worker('connection_broker_worker_threshold', 'conn_broker',
           'vim_broker_worker', BASE_PATH),
    Worker('reporting_worker_threshold', 'reporting',
           'reporting_worker', QUEUE_WORKER_PATH),
    Worker('web_service_worker_threshold', 'web_service',
           'web_service_worker', BASE_PATH),
    Worker('priority_worker_threshold', 'priority',
           'priority_worker', QUEUE_WORKER_PATH),
    Worker('cu_data_processor_worker_threshold', 'cu_data_proc',
           'ems_metrics_processor_worker', QUEUE_WORKER_PATH),
    Worker('refresh_worker_threshold', 'refresh',
           'ems_refresh_worker', QUEUE_WORKER_DEFAULTS_PATH),
    Worker('vm_analysis_collectors_worker_threshold',
           'vm_analysis', 'smart_proxy_worker', QUEUE_WORKER_PATH)
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
             num_sec=1800, delay=10, message="Wait for all original workers to be stopped")
    # And now check whether the same number of workers is back online
    wait_for(lambda: len(pids) == len(worker.get_all_worker_pids()),
             fail_func=worker.parent.reload_workers_page, num_sec=1800, delay=10,
             message="Wait for all original workers to be running")


v510 = {
    "1.1.gigabytes": 1178599424,
    1178599424: "1.1.gigabytes",
    "1.2.gigabytes": 1283457024,
    1283457024: "1.2.gigabytes"
}


def set_memory_threshold_in_ui(appliance, worker, new_threshold):
    view = navigate_to(appliance.server, 'Workers')
    view.browser.refresh()
    mem_threshold = getattr(view.workers, worker.dropdown)
    if appliance.version < '5.11' and new_threshold in v510:
        new_threshold = v510[new_threshold]
    mem_threshold.select_by_visible_text(new_threshold.replace('.gigabytes', ' GB'))
    view.workers.save.click()
    return new_threshold


def get_memory_threshold_in_advanced_settings(appliance, worker):
    worker_base = appliance.server.advanced_settings
    loc = worker_base
    steps = (['workers', 'worker_base'] +
             [step if step != '*' else worker.advanced for step in worker.path])
    for step in steps:
        worker_base = loc
        loc = loc.get(step)
    return loc.get('memory_threshold', worker_base['defaults']['memory_threshold'])


def set_memory_threshold_in_advanced_settings(appliance, worker, new_threshold):
    steps = (['workers', 'worker_base'] +
             [step if step != '*' else worker.advanced for step in worker.path])
    patch = {'memory_threshold': new_threshold}
    for step in steps[::-1]:
        patch = {step: patch}
    appliance.server.update_advanced_settings(patch)
    if appliance.version < '5.11' and new_threshold in v510:
        new_threshold = v510[new_threshold]
    return new_threshold


@test_requirements.settings
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1658373, 1715633, 1787350, 1799443, 1805845])
@pytest.mark.parametrize('set_memory_threshold',
    [set_memory_threshold_in_ui, set_memory_threshold_in_advanced_settings],
    ids=['in_UI', 'in_advanced_setting'])
@pytest.mark.parametrize('worker', WORKERS, ids=[x.id for x in WORKERS])
def test_set_memory_threshold(appliance, worker, request, set_memory_threshold):
    """
    Bugzilla:
        1656873
        1715633
        1787350
        1799443
        1805845

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/6h
    """
    view = navigate_to(appliance.server, 'Workers')
    before = get_memory_threshold_in_advanced_settings(appliance, worker)
    threshold_change = "1.1.gigabytes"
    other_change = "1.2.gigabytes"
    if set_memory_threshold == set_memory_threshold_in_advanced_settings:
        threshold_change, other_change = other_change, threshold_change
    if threshold_change in [before, v510.get(before)]:
        threshold_change = other_change
    if appliance.version < "5.11":
        threshold_change = v510[threshold_change]
    change = set_memory_threshold(appliance, worker, threshold_change)
    request.addfinalizer(
        lambda: set_memory_threshold_in_advanced_settings(appliance, worker, before)
    )

    def _ui_check():
        view.browser.refresh()
        mem_threshold = getattr(view.workers, worker.dropdown)
        after = mem_threshold.selected_option
        return after.startswith(change.replace(".gigabytes", " GB"))
    wait_for(_ui_check, delay=0, timeout=45)

    # check advanced settings
    change_val = float(change.replace('.gigabytes', ''))
    mem_threshold_real = get_memory_threshold_in_advanced_settings(appliance, worker)
    MESSAGE = "memory threshold have changed incorrectly in advanced settings"
    if appliance.version >= "5.11":
        assert mem_threshold_real == f"{change_val}.gigabytes", MESSAGE
    else:
        GB = 2 ** 30
        expected_value = change_val * GB
        # this tests if memory threshold has changed and is approximately correct
        assert abs(mem_threshold_real - expected_value) < expected_value * 0.01, MESSAGE
