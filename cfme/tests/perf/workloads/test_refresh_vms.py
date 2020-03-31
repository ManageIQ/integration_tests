"""Runs Refresh Workload by adding specified providers, and refreshing a specified number of vms,
waiting, then repeating for specified length of time."""
import time
from itertools import cycle

import pytest

from cfme.utils.conf import cfme_performance
from cfme.utils.grafana import get_scenario_dashboard_urls
from cfme.utils.log import logger
from cfme.utils.providers import get_crud
from cfme.utils.smem_memory_monitor import add_workload_quantifiers
from cfme.utils.smem_memory_monitor import SmemMemoryMonitor
from cfme.utils.workloads import get_refresh_vms_scenarios

FULL_REFRESH_THRESHOLD_DEFAULT = 100

roles_refresh_vms = ['automate', 'database_operations', 'ems_inventory', 'ems_operations',
    'event', 'reporting', 'scheduler', 'smartstate', 'user_interface', 'web_services', 'websocket']


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_refresh_vms_scenarios())
def test_refresh_vms(appliance, request, scenario):
    """Refreshes all vm's then waits for a specific amount of time. Memory Monitor creates
    graphs and summary at the end of the scenario.

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    from_ts = int(time.time() * 1000)
    logger.debug('Scenario: {}'.format(scenario['name']))

    appliance.clean_appliance()

    quantifiers = {}
    scenario_data = {'appliance_ip': appliance.hostname,
        'appliance_name': cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-refresh-vm',
        'test_name': 'Refresh VMs',
        'appliance_roles': ', '.join(roles_refresh_vms),
        'scenario': scenario}
    monitor_thread = SmemMemoryMonitor(appliance.ssh_client(), scenario_data)

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
    appliance.update_server_roles({role: True for role in roles_refresh_vms})
    for prov in scenario['providers']:
        get_crud(prov).create_rest()
    logger.info('Sleeping for refresh: {}s'.format(scenario['refresh_sleep_time']))
    time.sleep(scenario['refresh_sleep_time'])

    full_refresh_threshold_set = False
    if 'full_refresh_threshold' in scenario:
        if scenario['full_refresh_threshold'] != FULL_REFRESH_THRESHOLD_DEFAULT:
            appliance.set_full_refresh_threshold(scenario['full_refresh_threshold'])
            full_refresh_threshold_set = True
    if not full_refresh_threshold_set:
        logger.debug('Keeping full_refresh_threshold at default ({}).'.format(
            FULL_REFRESH_THRESHOLD_DEFAULT))

    refresh_size = scenario['refresh_size']

    vms = appliance.rest_api.collections.vms.all
    vms_iter = cycle(vms)
    logger.debug('Number of VM IDs: {}'.format(len(vms)))

    # Variable amount of time for refresh workload
    total_time = scenario['total_time']
    starttime = time.time()
    time_between_refresh = scenario['time_between_refresh']
    total_refreshed_vms = 0

    while ((time.time() - starttime) < total_time):
        start_refresh_time = time.time()
        refresh_list = [next(vms_iter) for x in range(refresh_size)]
        for vm in refresh_list:
            vm.action.reload()
        total_refreshed_vms += len(refresh_list)
        iteration_time = time.time()

        refresh_time = round(iteration_time - start_refresh_time, 2)
        elapsed_time = iteration_time - starttime
        logger.debug(f'Time to Queue VM Refreshes: {refresh_time}')
        logger.info('Time elapsed: {}/{}'.format(round(elapsed_time, 2), total_time))

        if refresh_time < time_between_refresh:
            wait_diff = time_between_refresh - refresh_time
            time_remaining = total_time - elapsed_time
            if (time_remaining > 0 and time_remaining < time_between_refresh):
                time.sleep(time_remaining)
            elif time_remaining > 0:
                time.sleep(wait_diff)
        else:
            logger.warning('Time to Queue VM Refreshes ({}) exceeded time between '
                '({})'.format(refresh_time, time_between_refresh))

    quantifiers['Elapsed_Time'] = round(time.time() - starttime, 2)
    quantifiers['Queued_VM_Refreshes'] = total_refreshed_vms
    logger.info('Test Ending...')
