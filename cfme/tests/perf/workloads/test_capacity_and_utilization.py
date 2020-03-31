"""Runs Capacity and Utilization Workload."""
import time

import pytest

from cfme.utils import conf
from cfme.utils.grafana import get_scenario_dashboard_urls
from cfme.utils.log import logger
from cfme.utils.providers import get_crud
from cfme.utils.smem_memory_monitor import add_workload_quantifiers
from cfme.utils.smem_memory_monitor import SmemMemoryMonitor
from cfme.utils.workloads import get_capacity_and_utilization_scenarios


roles_cap_and_util = ['automate', 'database_operations', 'ems_inventory', 'ems_metrics_collector',
    'ems_metrics_coordinator', 'ems_metrics_processor', 'ems_operations', 'event', 'notifier',
    'reporting', 'scheduler', 'user_interface', 'web_services']


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_capacity_and_utilization_scenarios())
def test_workload_capacity_and_utilization(request, scenario, appliance):
    """Runs through provider based scenarios enabling C&U and running for a set period of time.
    Memory Monitor creates graphs and summary at the end of each scenario.

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
        'test_dir': 'workload-cap-and-util',
        'test_name': 'Capacity and Utilization',
        'appliance_roles': ','.join(roles_cap_and_util),
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
    appliance.update_server_roles({role: True for role in roles_cap_and_util})
    for provider in scenario['providers']:
        get_crud(provider).create_rest()
    logger.info('Sleeping for Refresh: {}s'.format(scenario['refresh_sleep_time']))
    time.sleep(scenario['refresh_sleep_time'])
    appliance.set_cap_and_util_all_via_rails()

    # Variable amount of time for C&U collections/processing
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
