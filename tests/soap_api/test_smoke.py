'''
Created on April 11, 2013

@author: dgao
'''

import pytest
from soap_base import SoapClient
from time import time
from unittestzero import Assert

#class TestSmoke():
base = SoapClient()
client = base.client
vm_guid = None
request_id = None

def test_create_request():
	# Make psql call 
	psql_cmd = 'psql -d vmdb_production -c \'select name,guid from vms where template=true;\''
	ssh = base.ssh_client(user='root')
	ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(psql_cmd)

	# Find template guid
	template_guid = None

	for line in ssh_stdout.read().split('\n'):
		try:
			tmpl_name, tmpl_guid = line.split('|')
			if 'cfme' in tmpl_name:
				template_guid = tmpl_guid
				#logging.info('Using (%s,%s) template.' % (tmpl_name, tmpl_guid))
				break
		except ValueError:
			# probably hit an unpack error because header doesn't
			# have a delimiter
			continue

	# Generate provision request
	result = client.service.VmProvisionRequest('1.1', 
						'guid=%s' % template_guid, 
						'number_of_cpu=1|vm_memory=1024|vm_name=auto_test_vm', 
						'owner_first_name=tester|owner_last_name=testee|owner_email=test@redhat.com', 
						'', '')
	#print "this is the prov_request result:",result
	request_id = result.id

def test_check_request_status():
	start_time = time()
	while (time() - start_time < 300): # Give EVM 5 mins to move to change status
		result = client.service.GetVmProvisionRequest(request_id)
		#print "this is the get_prov_request result:", result
		if result.approval_state == 'approved':
			Assert.equal(result.status, 'Ok')

			vm_guid = result.vms[0].guid
			break
		time.sleep(30) # 30s nap
	Assert.not_none(vm_guid)

def test_get_vm():
	result = client.service.EVMGetVm(vm_guid)
	#print "this is the get_vm result:",result
	Assert.equal(result.name, 'auto_test_vm')
	Assert.equal(result.guid, vm_guid)

def test_start_vm():
	result = client.service.EVMSmartStart(vm_guid)
	#print "this is the start_vm result:",result
	Assert.equal(result.result, 'true')
	return test_check_request_status

# find a way to get VM status. i.e. 'starting', 'started/on', 'off'?
#def test_get_vm_status():
#	result = self.client.service.GetVmList(self.vm_guid)

def test_stop_vm():
	result = client.service.EVMSmartStart(vm_guid)
	#print "this is the stop_vm result:",result
	Assert.equal(result.result, 'true')
	return test_start_vm

def test_delete_vm():
	result = client.service.EVMDeleteVmByName('auto_test_vm')
	#print "this is the delete_vm result:",result
	Assert.equal(result.result, 'true')
