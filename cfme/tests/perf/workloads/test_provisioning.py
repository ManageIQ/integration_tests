"""Runs Provisioning Workload."""
import time
from itertools import cycle

import fauxfactory
import pytest

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.utils.conf import cfme_performance
from cfme.utils.grafana import get_scenario_dashboard_urls
from cfme.utils.log import logger
from cfme.utils.providers import get_crud
from cfme.utils.rest import assert_response
from cfme.utils.smem_memory_monitor import add_workload_quantifiers
from cfme.utils.smem_memory_monitor import SmemMemoryMonitor
from cfme.utils.smem_memory_monitor import test_ts
from cfme.utils.wait import wait_for
from cfme.utils.workloads import get_provisioning_scenarios


roles_provisioning = ['automate', 'database_operations', 'ems_inventory', 'ems_operations',
    'event', 'notifier', 'reporting', 'scheduler', 'user_interface', 'web_services']

roles_provisioning_cleanup = ['database_operations', 'ems_inventory', 'ems_operations',
    'event', 'notifier', 'reporting', 'scheduler', 'user_interface', 'web_services']


def get_provision_data(rest_api, provider, template_name, auto_approve=True):
    templates = rest_api.collections.templates.find_by(name=template_name)
    for template in templates:
        try:
            ems_id = template.ems_id
        except AttributeError:
            continue
        if ems_id == provider.id:
            guid = template.guid
            break
    else:
        raise Exception(f"No such template {template_name} on provider!")

    result = {
        "version": "1.1",
        "template_fields": {
            "guid": guid
        },
        "vm_fields": {
            "number_of_cpus": 1,
            "vm_name": fauxfactory.gen_alphanumeric(20, start="test_rest_prov_"),
            "vm_memory": "2048",
            "vlan": provider.data["provisioning"]["vlan"],
        },
        "requester": {
            "user_name": "admin",
            "owner_first_name": "John",
            "owner_last_name": "Doe",
            "owner_email": "jdoe@sample.com",
            "auto_approve": auto_approve
        },
        "tags": {
            "network_location": "Internal",
            "cc": "001"
        },
        "additional_values": {
            "request_id": "1001"
        },
        "ems_custom_attributes": {},
        "miq_custom_attributes": {}
    }

    if provider.one_of(RHEVMProvider):
        result["vm_fields"]["provision_type"] = "native_clone"
    return result


@pytest.mark.usefixtures('generate_version_files')
@pytest.mark.parametrize('scenario', get_provisioning_scenarios())
def test_provisioning(appliance, request, scenario):
    """Runs through provisioning scenarios using the REST API to
    continously provision a VM for a specified period of time.
    Memory Monitor creates graphs and summary at the end of each scenario.

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """

    from_ts = int(time.time() * 1000)
    logger.debug('Scenario: {}'.format(scenario['name']))

    appliance.clean_appliance()

    quantifiers = {}
    scenario_data = {'appliance_ip': appliance.hostname,
        'appliance_name': cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-provisioning',
        'test_name': 'Provisioning',
        'appliance_roles': ', '.join(roles_provisioning),
        'scenario': scenario}
    monitor_thread = SmemMemoryMonitor(appliance.ssh_client(), scenario_data)

    provision_order = []

    def cleanup_workload(scenario, from_ts, vms_to_cleanup, quantifiers, scenario_data):
        starttime = time.time()
        to_ts = int(starttime * 1000)
        g_urls = get_scenario_dashboard_urls(scenario, from_ts, to_ts)
        logger.debug('Started cleaning up monitoring thread.')
        appliance.update_server_roles({role: True for role in roles_provisioning_cleanup})
        monitor_thread.grafana_urls = g_urls
        monitor_thread.signal = False
        final_vm_size = len(vms_to_cleanup)
        appliance.rest_api.collections.vms.action.delete(vms_to_cleanup)
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
        logger.info(f'Finished cleaning up monitoring thread in {timediff}')

    request.addfinalizer(lambda: cleanup_workload(scenario, from_ts, vm_name, quantifiers,
            scenario_data))

    monitor_thread.start()

    appliance.wait_for_miq_server_workers_started(poll_interval=2)
    appliance.update_server_roles({role: True for role in roles_provisioning})
    prov = get_crud(scenario['providers'][0])
    prov.create_rest()
    logger.info('Sleeping for Refresh: {}s'.format(scenario['refresh_sleep_time']))
    time.sleep(scenario['refresh_sleep_time'])

    guid_list = prov.get_template_guids(scenario['templates'])
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
            vm_to_provision = 'test-{}-prov-{}'.format(
                test_ts, str(total_provisioned_vms).zfill(4))
            guid_to_provision, provider_name = next(guid_cycle)
            provision_order.append((vm_to_provision, provider_name))
            provision_list.append((vm_to_provision, guid_to_provision,
                prov.data['provisioning']['vlan']))

        template = prov.data.templates.get('small_template')
        provision_data = get_provision_data(appliance.rest_api, prov, template.name)
        vm_name = provision_data["vm_fields"]["vm_name"]
        response = appliance.rest_api.collections.provision_requests.action.create(**provision_data)
        assert_response(appliance)
        provision_request = response[0]

        def _finished():
            provision_request.reload()
            if "error" in provision_request.status.lower():
                pytest.fail(f"Error when provisioning: `{provision_request.message}`")
            return provision_request.request_state.lower() in ("finished", "provisioned")

        wait_for(_finished, num_sec=800, delay=5, message="REST provisioning finishes")

        vm = appliance.rest_api.collections.vms.get(name=vm_name)
        creation_time = time.time()
        provision_time = round(creation_time - start_iteration_time, 2)
        logger.debug(f'Time to initiate provisioning: {provision_time}')
        logger.info(f'{total_provisioned_vms} VMs provisioned so far')

        if provisioned_vms > cleanup_size * len(scenario['providers']):
            start_remove_time = time.time()
            if appliance.rest_api.collections.vms.action.delete(vm):
                provision_order.pop(0)
                provisioned_vms -= 1
                total_deleted_vms += 1
            deletion_time = round(time.time() - start_remove_time, 2)
            logger.debug(f'Time to initate deleting: {deletion_time}')
            logger.info(f'{total_deleted_vms} VMs deleted so far')

        end_iteration_time = time.time()
        iteration_time = round(end_iteration_time - start_iteration_time, 2)
        elapsed_time = end_iteration_time - starttime
        logger.debug(f'Time to initiate provisioning and deletion: {iteration_time}')
        logger.info('Time elapsed: {}/{}'.format(round(elapsed_time, 2), total_time))

        if iteration_time < time_between_provision:
            wait_diff = time_between_provision - iteration_time
            time_remaining = total_time - elapsed_time
            if (time_remaining > 0 and time_remaining < time_between_provision):
                time.sleep(time_remaining)
            elif time_remaining > 0:
                time.sleep(wait_diff)
            else:
                logger.warning('Time to initiate provisioning ({}) exceeded time between '
                    '({})'.format(iteration_time, time_between_provision))

    quantifiers['Elapsed_Time'] = round(time.time() - starttime, 2)
    quantifiers['Queued_VM_Provisionings'] = total_provisioned_vms
    quantifiers['Deleted_VMs'] = total_deleted_vms
    logger.info('Provisioned {} VMs and deleted {} VMs during the scenario.'
                .format(total_provisioned_vms, total_deleted_vms))
    logger.info('Test Ending...')
