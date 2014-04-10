'''
Created on April 11, 2013

@author: dgao
'''

import logging
from time import time, sleep

import pytest
from unittestzero import Assert

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skip_selenium,
    pytest.mark.nondestructive,
]

request_id = None
vm_guid = None
vm_name = 'auto-test-vm'

# Appliance needs to allow DB connections and support provisioning, one or both
# of which have been broken in 5.2 builds. Once those work, these tests will be
# addressed alongside automated provisioning via a fixture for distributed
# appliance testing.
skipmsg = """Skipping this test until we've got a working 5.2 appliance
For more info: https://github.com/RedHatQE/cfme_tests/issues/64
"""
# Adding the skip mark to all tests in here for now...
pytestmark.append(pytest.mark.skipif("skipmsg"))

def test_create_request(db, soap_client):
    global request_id
    vms_table = db['vms']

    # Find template guid
    template_guid = None
    for name, guid in db.session.query(vms_table.guid).filter(vms_table.template==True):
        if 'cfme' in name.lower():
            template_guid = guid.strip()
            logging.info('Using (%s,%s) template.' % (name, guid))
            break
    else:
        raise Exception("Couldn't find CFME template for provisioning smoke test")

    Assert.not_none(template_guid)
    # Generate provision request
    template_fields = soap_client.pipeoptions({
        'guid': template_guid,
    })

    # VMWare
    vm_fields = soap_client.pipeoptions({
        'number_of_cpu': 1,
        'vm_memory': 1024,
        'vm_name': vm_name,
    })

    requester = soap_client.pipeoptions({
        'owner_first_name': 'tester',
        'owner_last_name': 'testee',
        'owner_email': 'test@redhat.com',
    })
    result = soap_client.service.VmProvisionRequest('1.1',
        template_fields, vm_fields, requester, '', '')

    request_id = result.id

def test_check_request_status(soap_client):
    global vm_guid
    Assert.not_none(request_id)

    start_time = time()
    while (time() - start_time < 300): # Give EVM 5 mins to change status
        result = soap_client.service.GetVmProvisionRequest(request_id)
        if result.approval_state == 'approved':
            if result.status == 'Error':
                pytest.fail(result.message)

            Assert.equal(result.status, 'Ok')

            try:
                global vm_guid
                vm_guid = result.vms[0].guid
            except IndexError:
                # So result.vms was []
                logging.info('Result from provision request \
                    did not have any VM associated with it: %s' % result.vms)
            break
        sleep(30) # 30s nap

def test_get_vm(soap_client):
    Assert.not_none(vm_guid)

    result = soap_client.service.EVMGetVm(vm_guid)
    Assert.equal(result.name, vm_name)
    Assert.equal(result.guid, vm_guid)

def test_start_vm(soap_client):
    Assert.not_none(vm_guid)

    result = soap_client.service.EVMSmartStart(vm_guid)
    Assert.equal(result.result, 'true')
    return test_check_request_status

def test_stop_vm(soap_client):
    Assert.not_none(vm_guid)

    result = soap_client.service.EVMSmartStart(vm_guid)
    Assert.equal(result.result, 'true')
    return test_start_vm

def test_delete_vm(mgmt_sys_api_clients, soap_client):
    # TODO: Insert some smart logic to figure out which mgmt_sys
    # was the VM launched on, instead of calling delete from all.
    for mgmt_sys in mgmt_sys_api_clients.values():
        result = mgmt_sys.delete_vm(vm_name)

    # Now remove the VM from VMDB
    result = soap_client.service.EVMDeleteVmByName(vm_name)
    Assert.equal(result.result, 'true')
