"""Runs Provisioning Workload."""
from utils.appliance import clean_appliance
from utils.appliance import get_server_roles_workload_provisioning
from utils.appliance import set_server_roles_workload_provisioning
from utils.appliance import set_server_roles_workload_provisioning_cleanup
from utils.appliance import wait_for_miq_server_workers_started
from utils.conf import cfme_performance
from utils.grafana import get_scenario_dashboard_urls
from utils.log import logger
from utils.providers import add_providers
from utils.providers import delete_provisioned_vm
from utils.providers import delete_provisioned_vms
from utils.providers import provision_vm
from utils.providers import get_template_guids
from utils.smem_memory_monitor import add_workload_quantifiers
from utils.smem_memory_monitor import SmemMemoryMonitor
from utils.smem_memory_monitor import test_ts
from utils.ssh import SSHClient
from utils.workloads import get_provisioning_scenarios
from itertools import cycle
import time
import pytest


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_provisioning_scenarios())
def test_provisioning(request, scenario):
    """Runs through provisioning scenarios using the REST API to
    continously provision a VM for a specified period of time.
    Memory Monitor creates graphs and summary at the end of each scenario."""

    from_ts = int(time.time() * 1000)
    ssh_client = SSHClient()
    logger.debug('Scenario: {}'.format(scenario['name']))

    clean_appliance(ssh_client)

    quantifiers = {}
    scenario_data = {'appliance_ip': cfme_performance['appliance']['ip_address'],
        'appliance_name': cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-provisioning',
        'test_name': 'Provisioning',
        'appliance_roles': get_server_roles_workload_provisioning(separator=', '),
        'scenario': scenario}
    monitor_thread = SmemMemoryMonitor(SSHClient(), scenario_data)

    provision_order = []

    def cleanup_workload(scenario, from_ts, vms_to_cleanup, quantifiers, scenario_data):
        starttime = time.time()
        to_ts = int(starttime * 1000)
        g_urls = get_scenario_dashboard_urls(scenario, from_ts, to_ts)
        logger.debug('Started cleaning up monitoring thread.')
        set_server_roles_workload_provisioning_cleanup(ssh_client)
        monitor_thread.grafana_urls = g_urls
        monitor_thread.signal = False
        final_vm_size = len(vms_to_cleanup)
        delete_provisioned_vms(vms_to_cleanup)
        monitor_thread.join()
        logger.info('{} VMs were left over, and {} VMs were deleted in the finalizer.'
            .format(final_vm_size, final_vm_size - len(vms_to_cleanup)))
        logger.info('The following VMs were left over after the test: {}'
            .format(vms_to_cleanup))
        quantifiers['VMs_To_Delete_In_Finalizer'] = final_vm_size
        quantifiers['VMs_Deleted_In_Finalizer'] = final_vm_size - len(vms_to_cleanup)
        quantifiers['Leftover_VMs'] = vms_to_cleanup
        add_workload_quantifiers(quantifiers, scenario_data)
        timediff = time.time() - starttime
        logger.info('Finished cleaning up monitoring thread in {}'.format(timediff))

    request.addfinalizer(lambda: cleanup_workload(scenario, from_ts, provision_order, quantifiers,
            scenario_data))

    monitor_thread.start()

    wait_for_miq_server_workers_started(poll_interval=2)
    set_server_roles_workload_provisioning(ssh_client)
    add_providers(scenario['providers'])
    logger.info('Sleeping for Refresh: {}s'.format(scenario['refresh_sleep_time']))
    time.sleep(scenario['refresh_sleep_time'])

    guid_list = get_template_guids(scenario['templates'])
    guid_cycle = cycle(guid_list)
    cleanup_size = scenario['cleanup_size']
    number_of_vms = scenario['number_of_vms']
    total_time = scenario['total_time']
    time_between_provision = scenario['time_between_provision']
    total_provisioned_vms = 0
    total_deleted_vms = 0
    provisioned_vms = 0
    starttime = time.time()

    while ((time.time() - starttime) < total_time):
        start_iteration_time = time.time()
        provision_list = []
        for i in range(number_of_vms):
            total_provisioned_vms += 1
            provisioned_vms += 1
            vm_to_provision = '{}-provision-{}'.format(
                test_ts, str(total_provisioned_vms).zfill(4))
            guid_to_provision, provider_name = next(guid_cycle)
            provider_to_provision = cfme_performance['providers'][provider_name]
            provision_order.append((vm_to_provision, provider_name))
            provision_list.append((vm_to_provision, guid_to_provision,
                provider_to_provision['vlan_network']))

        provision_vm(provision_list)
        creation_time = time.time()
        provision_time = round(creation_time - start_iteration_time, 2)
        logger.debug('Time to initiate provisioning: {}'.format(provision_time))
        logger.info('{} VMs provisioned so far'.format(total_provisioned_vms))

        if provisioned_vms > cleanup_size * len(scenario['providers']):
            start_remove_time = time.time()
            if delete_provisioned_vm(provision_order[0]):
                provision_order.pop(0)
                provisioned_vms -= 1
                total_deleted_vms += 1
            deletion_time = round(time.time() - start_remove_time, 2)
            logger.debug('Time to initate deleting: {}'.format(deletion_time))
            logger.info('{} VMs deleted so far'.format(total_deleted_vms))

        end_iteration_time = time.time()
        iteration_time = round(end_iteration_time - start_iteration_time, 2)
        elapsed_time = end_iteration_time - starttime
        logger.debug('Time to initiate provisioning and deletion: {}'.format(iteration_time))
        logger.info('Time elapsed: {}/{}'.format(round(elapsed_time, 2), total_time))

        if iteration_time < time_between_provision:
            wait_diff = time_between_provision - iteration_time
            time_remaining = total_time - elapsed_time
            if (time_remaining > 0 and time_remaining < time_between_provision):
                time.sleep(time_remaining)
            elif time_remaining > 0:
                time.sleep(wait_diff)
            else:
                logger.warn('Time to initiate provisioning ({}) exceeded time between '
                    '({})'.format(iteration_time, time_between_provision))

    quantifiers['Elapsed_Time'] = round(time.time() - starttime, 2)
    quantifiers['Queued_VM_Provisionings'] = total_provisioned_vms
    quantifiers['Deleted_VMs'] = total_deleted_vms
    logger.info('Provisioned {} VMs and deleted {} VMs during the scenario.'
        .format(total_provisioned_vms, total_deleted_vms))
    logger.info('Test Ending...')
