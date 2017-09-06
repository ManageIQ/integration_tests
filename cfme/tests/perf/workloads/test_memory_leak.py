"""Runs Capacity and Utilization Workload."""

from utils import conf
from utils.appliance.implementations.ui import navigate_to
from utils.grafana import get_scenario_dashboard_urls
from utils.log import logger
from utils.smem_memory_monitor import add_workload_quantifiers, SmemMemoryMonitor
from utils.workloads import get_memory_leak_scenarios
import time
import pytest

pytestmark = [pytest.mark.meta(
    server_roles="+automate +ems_metrics_collector +ems_metrics_coordinator +ems_metrics_processor")
]


def prepare_workers(appliance):
    """Set single instance of each worker type and maximum threshold"""
    view = navigate_to(appliance.server, 'Workers')
    view.workers.generic_worker_count.fill('1')
    view.workers.cu_data_collector_worker_count.fill('1')
    view.workers.ui_worker_count.fill('1')
    view.workers.reporting_worker_count.fill('1')
    view.workers.web_service_worker_count.fill('1')
    view.workers.priority_worker_count.fill('1')
    view.workers.cu_data_processor_worker_count.fill('1')
    view.workers.vm_analysis_collectors_worker_count.fill('1')
    view.workers.websocket_worker_count.fill('1')

    view.workers.generic_worker_threshold.fill('1.5 GB')
    view.workers.cu_data_collector_worker_threshold.fill('1.5 GB')
    view.workers.event_monitor_worker_threshold.fill('10 GB')
    view.workers.connection_broker_worker_threshold.fill('10 GB')
    view.workers.reporting_worker_threshold.fill('1.5 GB')
    view.workers.web_service_worker_threshold.fill('1.5 GB')
    view.workers.priority_worker_threshold.fill('1.5 GB')
    view.workers.cu_data_processor_worker_threshold.fill('1.5 GB')
    view.workers.refresh_worker_threshold.fill('10 GB')
    view.workers.vm_analysis_collectors_worker_threshold.fill('1.5 GB')
    view.workers.save.click()


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_memory_leak_scenarios())
def test_workload_memory_leak(request, scenario, appliance, setup_only_one_provider):
    """Runs through provider based scenarios setting one worker instance and maximum threshold and
    running for a set period of time. Memory Monitor creates graphs and summary info."""
    from_ts = int(time.time() * 1000)
    logger.debug('Scenario: {}'.format(scenario['name']))

    appliance.clean_appliance()

    quantifiers = {}
    scenario_data = {'appliance_ip': appliance.hostname,
        'appliance_name': conf.cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-memory-leak',
        'test_name': 'Memory Leak',
        'appliance_roles': ','.join(appliance.server_roles),
        'scenario': scenario}
    monitor_thread = SmemMemoryMonitor(appliance.ssh_client, scenario_data)

    def cleanup_workload(scenario, from_ts, quantifiers, scenario_data):
        starttime = time.time()
        to_ts = int(starttime * 1000)
        g_urls = get_scenario_dashboard_urls(scenario, from_ts, to_ts)
        logger.debug('Started cleaning up monitoring thread.')
        monitor_thread.grafana_urls = g_urls
        monitor_thread.signal = False
        monitor_thread.join()
        add_workload_quantifiers(quantifiers, scenario_data)
        timediff = time.time() - starttime
        logger.info('Finished cleaning up monitoring thread in {}'.format(timediff))
    request.addfinalizer(lambda: cleanup_workload(scenario, from_ts, quantifiers, scenario_data))

    monitor_thread.start()

    appliance.wait_for_miq_server_workers_started(poll_interval=2)
    prepare_workers(appliance)
    logger.info('Sleeping for Refresh: {}s'.format(scenario['refresh_sleep_time']))
    time.sleep(scenario['refresh_sleep_time'])

    total_time = scenario['total_time']
    starttime = time.time()
    elapsed_time = 0
    while (elapsed_time < total_time):
        elapsed_time = time.time() - starttime
        time_left = total_time - elapsed_time
        logger.info('Time elapsed: {}/{}'.format(round(elapsed_time, 2), total_time))
        if (time_left > 0 and time_left < 300):
            time.sleep(time_left)
        elif time_left > 0:
            time.sleep(300)

    quantifiers['Elapsed_Time'] = round(elapsed_time, 2)
    logger.info('Test Ending...')
