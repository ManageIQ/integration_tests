import time

import pytest

from cfme.markers.env_markers.provider import providers
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.grafana import get_scenario_dashboard_urls
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.smem_memory_monitor import add_workload_quantifiers
from cfme.utils.smem_memory_monitor import SmemMemoryMonitor
from cfme.utils.workloads import get_memory_leak_scenarios


roles_memory_leak = ['automate', 'database_operations', 'ems_inventory', 'ems_metrics_collector',
    'ems_metrics_coordinator', 'ems_metrics_processor', 'ems_operations', 'event', 'notifier',
    'reporting', 'scheduler', 'user_interface', 'web_services']


pytestmark = [pytest.mark.provider(gen_func=providers,
                                   filters=[ProviderFilter()],
                                   scope="module")]


def prepare_workers(appliance):
    """Set single instance of each worker type and maximum threshold"""
    view = navigate_to(appliance.server, 'Workers')
    view.workers.fill({
        "generic_worker_count": "1",
        "cu_data_collector_worker_count": "1",
        "ui_worker_count": "1",
        "reporting_worker_count": "1",
        "web_service_worker_count": "1",
        "priority_worker_count": "1",
        "cu_data_processor_worker_count": "1",
        "vm_analysis_collectors_worker_count": "1",
        "websocket_worker_count": "1",
        "generic_worker_threshold": "1.5 GB",
        "cu_data_collector_worker_threshold": "1.5 GB",
        "event_monitor_worker_threshold": "10 GB",
        "connection_broker_worker_threshold": "10 GB",
        "reporting_worker_threshold": "1.5 GB",
        "web_service_worker_threshold": "1.5 GB",
        "priority_worker_threshold": "1.5 GB",
        "cu_data_processor_worker_threshold": "1.5 GB",
        "refresh_worker_threshold": "10 GB",
        "vm_analysis_collectors_worker_threshold": "1.5 GB"
    })
    view.workers.save.click()


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_memory_leak_scenarios())
def test_workload_memory_leak(request, scenario, appliance, provider):
    """Runs through provider based scenarios setting one worker instance and maximum threshold and
    running for a set period of time. Memory Monitor creates graphs and summary info.

    Polarion:
        assignee: rhcf3_machine
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    from_ts = int(time.time() * 1000)
    logger.debug('Scenario: {}'.format(scenario['name']))

    appliance.clean_appliance()

    quantifiers = {}
    scenario_data = {'appliance_ip': appliance.hostname,
        'appliance_name': conf.cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-memory-leak',
        'test_name': 'Memory Leak',
        'appliance_roles': ','.join(roles_memory_leak),
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
        logger.info(f'Finished cleaning up monitoring thread in {timediff}')
    request.addfinalizer(lambda: cleanup_workload(scenario, from_ts, quantifiers, scenario_data))

    monitor_thread.start()

    appliance.wait_for_miq_server_workers_started(poll_interval=2)
    appliance.update_server_roles({role: True for role in roles_memory_leak})
    prepare_workers(appliance)
    provider.create()

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
