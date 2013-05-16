'''
Created on April 11, 2013

@author: dgao
'''

import pytest
import logging
from soap_base import SoapClient
from time import time, sleep
from unittestzero import Assert

vm_guid = None
request_id = None

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]

@pytest.fixture(scope='module')
def soap_base(mozwebqa, cfme_data):
    return SoapClient(mozwebqa, cfme_data)

@pytest.fixture(scope='module')
def soap_client(soap_base):
    return soap_base.client

@pytest.fixture(scope='module')
def api_clients(soap_base):
    clients = soap_base.setup_mgmt_clients()
    return clients

def test_create_request(mozwebqa, soap_base, soap_client):
    # Make psql call 
    psql_cmd = 'psql -d vmdb_production -c \'select name,guid from vms where template=true;\''
    ssh = soap_base.ssh_client(user='root')
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(psql_cmd)

    # Find template guid
    template_guid = None

    for line in ssh_stdout.read().split('\n'):
        try:
            tmpl_name, tmpl_guid = line.split('|')
            if 'cfme' in tmpl_name:
                template_guid = tmpl_guid.strip()
                logging.info('Using (%s,%s) template.' % (tmpl_name, tmpl_guid))
                break
        except ValueError:
            # probably hit an unpack error because header doesn't
            # have a delimiter
            continue

    # Generate provision request
    result = soap_client.service.VmProvisionRequest('1.1', 
                'guid=%s' % template_guid, 
                'number_of_cpu=1|vm_memory=1024|vm_name=auto_test_vm', 
                'owner_first_name=tester|owner_last_name=testee|owner_email=test@redhat.com', 
                '', '')

    global request_id
    request_id = result.id

def test_check_request_status(mozwebqa, soap_client):
    start_time = time()
    while (time() - start_time < 300): # Give EVM 5 mins to change status
        result = soap_client.service.GetVmProvisionRequest(request_id)
        if result.approval_state == 'approved':
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
    Assert.not_none(vm_guid)

def test_get_vm(mozwebqa, soap_client):
    result = soap_client.service.EVMGetVm(vm_guid)
    Assert.equal(result.name, 'auto_test_vm')
    Assert.equal(result.guid, vm_guid)

def test_start_vm(mozwebqa, soap_client):
    result = soap_client.service.EVMSmartStart(vm_guid)
    Assert.equal(result.result, 'true')
    return test_check_request_status

# find a way to get VM status. i.e. 'starting', 'started/on', 'off'?
#def test_get_vm_status():
#	result = self.client.service.GetVmList(self.vm_guid)

def test_stop_vm(mozwebqa, soap_client):
    result = soap_client.service.EVMSmartStart(vm_guid)
    Assert.equal(result.result, 'true')
    return test_start_vm

def test_delete_vm(mozwebqa, soap_client, api_clients):
    result = soap_client.service.EVMDeleteVmByName('auto_test_vm')
    Assert.equal(result.result, 'true')
    for mgmt_sys in api_clients:
        result = mgmt_sys.delete_vm('auto_test_vm')
