"""Runs Capacity and Utilization with Replication Workload."""
import time

import pytest

from cfme.utils.appliance import DefaultAppliance
from cfme.utils.conf import cfme_performance
from cfme.utils.grafana import get_scenario_dashboard_urls
from cfme.utils.log import logger
from cfme.utils.providers import get_crud
from cfme.utils.smem_memory_monitor import add_workload_quantifiers
from cfme.utils.smem_memory_monitor import SmemMemoryMonitor
from cfme.utils.ssh import SSHClient
from cfme.utils.ssh import SSHTail
from cfme.utils.workloads import get_capacity_and_utilization_replication_scenarios

roles_cap_and_util_rep = ['automate', 'database_operations', 'database_synchronization',
                      'ems_inventory', 'ems_metrics_collector', 'ems_metrics_coordinator',
                      'ems_metrics_processor', 'ems_operations', 'event', 'notifier',
                      'reporting', 'scheduler', 'user_interface', 'web_services']


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_capacity_and_utilization_replication_scenarios())
def test_workload_capacity_and_utilization_rep(appliance, request, scenario, setup_perf_provider):
    """Runs through provider based scenarios enabling C&U and replication, run for a set period of
    time. Memory Monitor creates graphs and summary at the end of each scenario.

    Polarion:
        assignee: rhcf3_machine
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    from_ts = int(time.time() * 1000)
    ssh_client = appliance.ssh_client()

    ssh_master_args = {
        'hostname': scenario['replication_master']['ip_address'],
        'username': scenario['replication_master']['ssh']['username'],
        'password': scenario['replication_master']['ssh']['password']}
    master_appliance = DefaultAppliance(hostname=scenario['replication_master']['ip_address'],
                                        openshift_creds=ssh_master_args)

    ssh_client_master = SSHClient(**ssh_master_args)
    logger.debug('Scenario: {}'.format(scenario['name']))

    is_pglogical = True if scenario['replication'] == 'pglogical' else False

    # Turn off master pglogical replication incase rubyrep scenario follows a pglogical scenario
    appliance.set_pglogical_replication(replication_type=':none')
    # Spawn tail before hand to prevent unncessary waiting on MiqServer starting since applinace
    # under test is cleaned first, followed by master appliance
    sshtail_evm = SSHTail('/var/www/miq/vmdb/log/evm.log')
    sshtail_evm.set_initial_file_end()
    logger.info(f'Clean appliance under test ({ssh_client})')
    appliance.clean_appliance()
    logger.info(f'Clean master appliance ({ssh_client_master})')
    master_appliance.clean_appliance()  # Clean Replication master appliance

    if is_pglogical:
        scenario_data = {'appliance_ip': appliance.hostname,
            'appliance_name': cfme_performance['appliance']['appliance_name'],
            'test_dir': 'workload-cap-and-util-rep',
            'test_name': 'Capacity and Utilization Replication (pgLogical)',
            'appliance_roles': ', '.join(roles_cap_and_util_rep),
            'scenario': scenario}
    else:
        scenario_data = {'appliance_ip': cfme_performance['appliance']['ip_address'],
            'appliance_name': cfme_performance['appliance']['appliance_name'],
            'test_dir': 'workload-cap-and-util-rep',
            'test_name': 'Capacity and Utilization Replication (RubyRep)',
            'appliance_roles': ', '.join(roles_cap_and_util_rep),
            'scenario': scenario}
    quantifiers = {}
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

    appliance.wait_for_miq_server_workers_started(evm_tail=sshtail_evm, poll_interval=2)
    appliance.update_server_roles({role: True for role in roles_cap_and_util_rep})
    for provider in scenario['providers']:
        get_crud(provider).create_rest()
    logger.info('Sleeping for Refresh: {}s'.format(scenario['refresh_sleep_time']))
    time.sleep(scenario['refresh_sleep_time'])
    appliance.set_cap_and_util_all_via_rails()

    # Configure Replication
    if is_pglogical:
        # Setup appliance under test to :remote
        appliance.set_pglogical_replication(replication_type=':remote')
        # Setup master appliance to :global
        master_appliance.set_pglogical_replication(replication_type=':global')
        # Setup master to subscribe:
        master_appliance.add_pglogical_replication_subscription(ssh_client_master,
            appliance.hostname)
    else:
        # Setup local towards Master
        appliance.set_rubyrep_replication(scenario['replication_master']['ip_address'])
        # Force uninstall rubyrep for this region from master (Unsure if still needed)
        # ssh_client.run_rake_command('evm:dbsync:uninstall')
        # time.sleep(30)  # Wait to quiecse
        # Turn on DB Sync role
        appliance.update_server_roles({role: True for role in roles_cap_and_util_rep})

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
        appliance.set_pglogical_replication(replication_type=':none')
    else:
        appliance.update_server_roles({role: True for role in roles_cap_and_util_rep})

    quantifiers['Elapsed_Time'] = round(elapsed_time, 2)
    logger.info('Test Ending...')
