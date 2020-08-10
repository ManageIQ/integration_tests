from collections import namedtuple

import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log_validator import LogValidator
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


def set_memory_threshold_in_ui(appliance, worker, new_threshold):
    view = navigate_to(appliance.server, 'Workers')
    view.browser.refresh()
    mem_threshold = getattr(view.workers, worker.dropdown)
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
    return new_threshold


def _update_advanced_settings_restart(appliance, updates):
    appliance.update_advanced_settings(updates)
    appliance.evmserverd.restart()
    appliance.wait_for_miq_ready()


@test_requirements.settings
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1658373, 1715633, 1787350, 1799443, 1805845, 1810773])
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
        1810773

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
    if threshold_change == before:
        threshold_change = other_change
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
    assert mem_threshold_real == f"{change_val}.gigabytes", MESSAGE


@test_requirements.settings
@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1348625])
def test_verify_purging_of_old_records(request, appliance):
    """
    Verify that tables are being purged regularly.

    Bugzilla:
        1348625

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        initialEstimate: 1/6h
        startsin: 5.8
    """
    old_settings = appliance.advanced_settings

    @request.addfinalizer
    def _restore_advanced_settings():
        _update_advanced_settings_restart(appliance, old_settings)

    purge_settings = {
        'container_entities_purge_interval': '5.minutes',
        'binary_blob_purge_interval': '5.minutes',
        'compliance_purge_interval': '5.minutes',
        'drift_state_purge_interval': '5.minutes',
        'event_streams_purge_interval': '5.minutes',
        'notifications_purge_interval': '5.minutes',
        'performance_realtime_purging_interval': '5.minutes',
        'performance_rollup_purging_interval': '5.minutes',
        'policy_events_purge_interval': '5.minutes',
        'report_result_purge_interval': '5.minutes',
        'task_purge_interval': '5.minutes',
        'vim_performance_states_purge_interval': '5.minutes'
    }

    new_settings = {'workers': {'worker_base': {'schedule_worker': purge_settings}}}

    obj_types = (
        'Binary blobs',
        'Compliances',
        'Container groups',
        'Container images',
        'Container nodes',
        'Container projects',
        'Container quota items',
        'Container quotas',
        'Containers',
        'all daily metrics',
        'Drift states',
        'Event streams',
        'all hourly metrics',
        'Miq report results',
        'Miq tasks',
        'Notifications',
        'orphans in Vim performance states',
        'Policy events'
    )

    matched_patterns = [f"Purging {obj_type}" for obj_type in obj_types]

    with LogValidator(
        '/var/www/miq/vmdb/log/evm.log',
        matched_patterns=matched_patterns,
    ).waiting(wait=600, delay=30):
        _update_advanced_settings_restart(appliance, new_settings)
