"""Runs Refresh Workload by adding specified providers, refreshing the providers, waiting, then
repeating for specified length of time."""
from cfme.utils.conf import cfme_performance
from cfme.utils.grafana import get_scenario_dashboard_urls
from cfme.utils.log import logger
from cfme.utils.providers import get_crud
from cfme.utils.smem_memory_monitor import add_workload_quantifiers, SmemMemoryMonitor
from cfme.utils.workloads import get_refresh_providers_scenarios

import time
import pytest

roles_refresh_providers = ['automate', 'database_operations', 'ems_inventory', 'ems_operations',
    'event', 'reporting', 'scheduler', 'smartstate', 'user_interface', 'web_services', 'websocket']


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_refresh_providers_scenarios())
def test_refresh_providers(appliance, request, scenario):
    """
    Refreshes providers then waits for a specific amount of time.
    Memory Monitor creates graphs and summary at the end of the scenario.
    """
    from_ts = int(time.time() * 1000)
    logger.debug('Scenario: {}'.format(scenario['name']))

    appliance.clean_appliance()

    quantifiers = {}
    scenario_data = {
        'appliance_ip': appliance.hostname,
        'appliance_name': cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-refresh-providers',
        'test_name': 'Refresh Providers',
        'appliance_roles': ', '.join(roles_refresh_providers),
        'scenario': scenario
    }
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
        logger.info('Finished cleaning up monitoring thread in {}'.format(timediff))

    request.addfinalizer(lambda: cleanup_workload(scenario, from_ts,
                                                  quantifiers, scenario_data))
    monitor_thread.start()

    appliance.wait_for_miq_server_workers_started(poll_interval=2)
    appliance.update_server_roles({role: True for role in roles_refresh_providers})
    for prov in scenario['providers']:
        get_crud(prov).create_rest()

    # Variable amount of time for refresh workload
    total_time = scenario['total_time']
    starttime = time.time()
    time_between_refresh = scenario['time_between_refresh']
    total_refreshed_providers = 0

    while ((time.time() - starttime) < total_time):
        start_refresh_time = time.time()
        appliance.rest_api.collections.providers.reload()
        for prov in appliance.rest_api.collections.providers.all:
            prov.action.reload()
            total_refreshed_providers += 1
        iteration_time = time.time()

        refresh_time = round(iteration_time - start_refresh_time, 2)
        elapsed_time = iteration_time - starttime
        logger.debug('Time to Queue Refreshes: {}'.format(refresh_time))
        logger.info('Time elapsed: {}/{}'.format(round(elapsed_time, 2), total_time))

        if refresh_time < time_between_refresh:
            wait_diff = time_between_refresh - refresh_time
            time_remaining = total_time - elapsed_time
            if (time_remaining > 0 and time_remaining < time_between_refresh):
                time.sleep(time_remaining)
            elif time_remaining > 0:
                time.sleep(wait_diff)
        else:
            logger.warn('Time to Queue Refreshes ({}) exceeded time between '
                        '({})'.format(refresh_time, time_between_refresh))

    quantifiers['Elapsed_Time'] = round(time.time() - starttime, 2)
    quantifiers['Queued_Provider_Refreshes'] = total_refreshed_providers
    logger.info('Test Ending...')
