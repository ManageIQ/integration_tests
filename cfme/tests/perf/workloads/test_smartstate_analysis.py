"""Runs SmartState Analysis Workload."""
import time

import pytest

from cfme.infrastructure import host
from cfme.utils import conf
from cfme.utils.conf import cfme_performance
from cfme.utils.grafana import get_scenario_dashboard_urls
from cfme.utils.log import logger
from cfme.utils.providers import get_crud
from cfme.utils.smem_memory_monitor import add_workload_quantifiers
from cfme.utils.smem_memory_monitor import SmemMemoryMonitor
from cfme.utils.workloads import get_smartstate_analysis_scenarios

roles_smartstate = ['automate', 'database_operations', 'ems_inventory', 'ems_operations', 'event',
    'notifier', 'reporting', 'scheduler', 'smartproxy', 'smartstate', 'user_interface',
    'web_services']


def get_host_data_by_name(provider, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider.key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_smartstate_analysis_scenarios())
def test_workload_smartstate_analysis(appliance, request, scenario):
    """Runs through provider based scenarios initiating smart state analysis against VMs, Hosts,
    and Datastores

    Polarion:
        assignee: rhcf3_machine
        casecomponent: SmartState
        initialEstimate: 1/4h
    """
    from_ts = int(time.time() * 1000)
    logger.debug('Scenario: {}'.format(scenario['name']))
    appliance.install_vddk()

    appliance.clean_appliance()

    quantifiers = {}
    scenario_data = {'appliance_ip': appliance.hostname,
        'appliance_name': cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-ssa',
        'test_name': 'SmartState Analysis',
        'appliance_roles': ', '.join(roles_smartstate),
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
        logger.info('Finished cleaning up monitoring thread in {}'.format(timediff))
    request.addfinalizer(lambda: cleanup_workload(scenario, from_ts, quantifiers, scenario_data))

    monitor_thread.start()

    appliance.wait_for_miq_server_workers_started(poll_interval=2)
    appliance.update_server_roles({role: True for role in roles_smartstate})
    for provider in scenario['providers']:
        get_crud(provider).create_rest()
    logger.info('Sleeping for Refresh: {}s'.format(scenario['refresh_sleep_time']))
    time.sleep(scenario['refresh_sleep_time'])

    # Add host credentials and set CFME relationship for RHEVM SSA
    for provider in scenario['providers']:
        for api_host in appliance.rest_api.collections.hosts.all:
            host_collection = appliance.collections.hosts
            test_host = host_collection.instantiate(name=api_host.name, provider=provider)
            host_data = get_host_data_by_name(get_crud(provider), api_host.name)
            credentials = host.get_credentials_from_config(host_data['credentials'])
            test_host.update_credentials_rest(credentials)
        appliance.set_cfme_server_relationship(cfme_performance['appliance']['appliance_name'])

    # Variable amount of time for SmartState Analysis workload
    total_time = scenario['total_time']
    starttime = time.time()
    time_between_analyses = scenario['time_between_analyses']
    total_scanned_vms = 0

    while ((time.time() - starttime) < total_time):
        start_ssa_time = time.time()
        for vm in list(scenario['vms_to_scan'].values())[0]:
            vm_api = appliance.rest_api.collections.vms.get(name=vm)
            vm_api.action.scan()
            total_scanned_vms += 1
        iteration_time = time.time()

        ssa_time = round(iteration_time - start_ssa_time, 2)
        elapsed_time = iteration_time - starttime
        logger.debug('Time to Queue SmartState Analyses: {}'.format(ssa_time))
        logger.info('Time elapsed: {}/{}'.format(round(elapsed_time, 2), total_time))

        if ssa_time < time_between_analyses:
            wait_diff = time_between_analyses - ssa_time
            time_remaining = total_time - elapsed_time
            if (time_remaining > 0 and time_remaining < time_between_analyses):
                time.sleep(time_remaining)
            elif time_remaining > 0:
                time.sleep(wait_diff)
        else:
            logger.warn('Time to Queue SmartState Analyses ({}) exceeded time between '
                '({})'.format(ssa_time, time_between_analyses))

    quantifiers['Elapsed_Time'] = round(time.time() - starttime, 2)
    quantifiers['Queued_VM_Scans'] = total_scanned_vms
    logger.info('Test Ending...')
