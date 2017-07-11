"""Runs Refresh Workload by adding specified providers, refreshing the providers, waiting, then
repeating for specified length of time."""
from utils.appliance import clean_appliance
from utils.appliance import get_server_roles_workload_refresh_providers
from utils.appliance import set_server_roles_workload_refresh_providers
from utils.appliance import wait_for_miq_server_workers_started
from utils.conf import cfme_performance
from utils.grafana import get_scenario_dashboard_urls
from utils.log import logger
from utils.providers import add_providers
from utils.providers import get_all_provider_ids
from utils.providers import refresh_providers_bulk
from utils.smem_memory_monitor import add_workload_quantifiers
from utils.smem_memory_monitor import SmemMemoryMonitor
from utils.ssh import SSHClient
from utils.workloads import get_refresh_providers_scenarios
import time
import pytest


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_refresh_providers_scenarios())
def test_refresh_providers(request, scenario):
    """
    Refreshes providers then waits for a specific amount of time.
    Memory Monitor creates graphs and summary at the end of the scenario.
    """
    from_ts = int(time.time() * 1000)
    ssh_client = SSHClient()
    logger.debug('Scenario: {}'.format(scenario['name']))

    clean_appliance(ssh_client)

    quantifiers = {}
    scenario_data = {
        'appliance_ip': cfme_performance['appliance']['ip_address'],
        'appliance_name': cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-refresh-providers',
        'test_name': 'Refresh Providers',
        'appliance_roles': get_server_roles_workload_refresh_providers(separator=', '),
        'scenario': scenario
    }
    monitor_thread = SmemMemoryMonitor(SSHClient(), scenario_data)

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

    wait_for_miq_server_workers_started(poll_interval=2)
    set_server_roles_workload_refresh_providers(ssh_client)
    add_providers(scenario['providers'])
    id_list = get_all_provider_ids()

    # Variable amount of time for refresh workload
    total_time = scenario['total_time']
    starttime = time.time()
    time_between_refresh = scenario['time_between_refresh']
    total_refreshed_providers = 0

    while ((time.time() - starttime) < total_time):
        start_refresh_time = time.time()
        refresh_providers_bulk(id_list)
        total_refreshed_providers += len(id_list)
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
