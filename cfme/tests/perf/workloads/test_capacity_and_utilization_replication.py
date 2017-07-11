"""Runs Capacity and Utilization with Replication Workload."""
from utils.appliance import add_pglogical_replication_subscription
from utils.appliance import clean_appliance
from utils.appliance import get_server_roles_workload_cap_and_util
from utils.appliance import get_server_roles_workload_cap_and_util_rep
from utils.appliance import set_cap_and_util_all_via_rails
from utils.appliance import set_pglogical_replication
from utils.appliance import set_rubyrep_replication
from utils.appliance import set_server_roles_workload_cap_and_util
from utils.appliance import set_server_roles_workload_cap_and_util_rep
from utils.appliance import wait_for_miq_server_workers_started
from utils.conf import cfme_performance
from utils.grafana import get_scenario_dashboard_urls
from utils.log import logger
from utils.providers import add_providers
from utils.smem_memory_monitor import add_workload_quantifiers
from utils.smem_memory_monitor import SmemMemoryMonitor
from utils.ssh import SSHClient
from utils.ssh import SSHTail
from utils.workloads import get_capacity_and_utilization_replication_scenarios
import time
import pytest

roles_cap_and_util_rep = ['automate', 'database_operations', 'database_synchronization',
                      'ems_inventory', 'ems_metrics_collector', 'ems_metrics_coordinator',
                      'ems_metrics_processor', 'ems_operations', 'event', 'notifier',
                      'reporting', 'scheduler', 'user_interface', 'web_services']


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_capacity_and_utilization_replication_scenarios())
def test_workload_capacity_and_utilization_rep(request, scenario):
    """Runs through provider based scenarios enabling C&U and replication, run for a set period of
    time. Memory Monitor creates graphs and summary at the end of each scenario."""
    from_ts = int(time.time() * 1000)
    ssh_client = SSHClient()
    ssh_master_args = {
            'hostname': scenario['replication_master']['ip_address'],
            'username': scenario['replication_master']['ssh']['username'],
            'password': scenario['replication_master']['ssh']['password']
        }
    ssh_client_master = SSHClient(**ssh_master_args)
    logger.debug('Scenario: {}'.format(scenario['name']))

    is_pglogical = True if scenario['replication'] == 'pglogical' else False

    # Turn off master pglogical replication incase rubyrep scenario follows a pglogical scenario
    set_pglogical_replication(ssh_client_master, replication_type=':none')
    # Spawn tail before hand to prevent unncessary waiting on MiqServer starting since applinace
    # under test is cleaned first, followed by master appliance
    sshtail_evm = SSHTail('/var/www/miq/vmdb/log/evm.log')
    sshtail_evm.set_initial_file_end()
    logger.info('Clean appliance under test ({})'.format(ssh_client))
    clean_appliance(ssh_client)
    logger.info('Clean master appliance ({})'.format(ssh_client_master))
    clean_appliance(ssh_client_master, False)  # Clean Replication master appliance

    if is_pglogical:
        scenario_data = {'appliance_ip': cfme_performance['appliance']['ip_address'],
            'appliance_name': cfme_performance['appliance']['appliance_name'],
            'test_dir': 'workload-cap-and-util-rep',
            'test_name': 'Capacity and Utilization Replication (pgLogical)',
            'appliance_roles': get_server_roles_workload_cap_and_util(separator=', '),
            'scenario': scenario}
    else:
        scenario_data = {'appliance_ip': cfme_performance['appliance']['ip_address'],
            'appliance_name': cfme_performance['appliance']['appliance_name'],
            'test_dir': 'workload-cap-and-util-rep',
            'test_name': 'Capacity and Utilization Replication (RubyRep)',
            'appliance_roles': get_server_roles_workload_cap_and_util_rep(separator=', '),
            'scenario': scenario}
    quantifiers = {}
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
    request.addfinalizer(lambda: cleanup_workload(scenario, from_ts, quantifiers, scenario_data))

    monitor_thread.start()

    wait_for_miq_server_workers_started(evm_tail=sshtail_evm, poll_interval=2)
    set_server_roles_workload_cap_and_util(ssh_client)
    add_providers(scenario['providers'])
    logger.info('Sleeping for Refresh: {}s'.format(scenario['refresh_sleep_time']))
    time.sleep(scenario['refresh_sleep_time'])
    set_cap_and_util_all_via_rails(ssh_client)

    # Configure Replication
    if is_pglogical:
        # Setup appliance under test to :remote
        set_pglogical_replication(ssh_client, replication_type=':remote')
        # Setup master appliance to :global
        set_pglogical_replication(ssh_client_master, replication_type=':global')
        # Setup master to subscribe:
        add_pglogical_replication_subscription(ssh_client_master,
            cfme_performance['appliance']['ip_address'])
    else:
        # Setup local towards Master
        set_rubyrep_replication(ssh_client, scenario['replication_master']['ip_address'])
        # Force uninstall rubyrep for this region from master (Unsure if still needed)
        # ssh_client.run_rake_command('evm:dbsync:uninstall')
        # time.sleep(30)  # Wait to quiecse
        # Turn on DB Sync role
        set_server_roles_workload_cap_and_util_rep(ssh_client)

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

    # Turn off replication:
    if is_pglogical:
        set_pglogical_replication(ssh_client_master, replication_type=':none')
    else:
        set_server_roles_workload_cap_and_util(ssh_client)

    quantifiers['Elapsed_Time'] = round(elapsed_time, 2)
    logger.info('Test Ending...')
