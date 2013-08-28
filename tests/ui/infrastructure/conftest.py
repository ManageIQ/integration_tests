'''
@author: dajohnso
'''
# -*- coding: utf8 -*-
#pylint: disable=E1101

import pytest
import re
import time

ON_REGEX = re.compile(r'up|POWERED\ ON|running')
DOWN_REGEX = re.compile(r'down|POWERED\ OFF|stopped')
SUSPEND_REGEX = re.compile(r'SUSPENDED|suspended')

@pytest.fixture()
def load_providers_vm_list(
        cfme_data,
        infra_providers_pg,
        provider,
        vm_name=None):
    '''
        Load the vm list of a specific provider.  Will also find the page for a specific vm if name is passed

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :param vm_name: name of the vm to be started
        :type  vm_name: str
        :return: page for vm list
        :rtype: Services.VirtualMachines
    '''
    provider_details = infra_providers_pg.load_provider_details(
            cfme_data.data["management_systems"][provider]["name"])
    vm_pg = provider_details.all_vms()
    if vm_name is not None:
        vm_pg.find_vm_page(vm_name, None, False, False)
    return vm_pg

@pytest.fixture()
def load_vm_details(load_providers_vm_list, provider, vm_name):
    '''
        Load the vm details of a specific vm  

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :param vm_name: name of the vm 
        :type  vm_name: str
        :return: page for vm details
        :rtype: Services.VirtualMachinesDetails
    '''
    return load_providers_vm_list.find_vm_page(vm_name, None, False, True)

@pytest.fixture
def verify_vm_running(mgmt_sys_api_clients, provider, vm_name):
    '''
        Verifies the vm is in the running state for the test.  Uses calls to the actual provider api.  
          It will start the vm if necessary.

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :param vm_name: name of the vm 
        :type  vm_name: str
        :return: None
        :rtype: None
    '''
    count = 0
    while count < 10:
        state = mgmt_sys_api_clients[provider].vm_status(vm_name)
        if ON_REGEX.match(state):
            return
        elif DOWN_REGEX.match(state) or SUSPEND_REGEX.match(state):
            mgmt_sys_api_clients[provider].start_vm(vm_name)
        print "Sleeping 15secs...(current state: " + \
                state + ", needed state: running)"
        time.sleep(15)
        count += 1
    raise Exception("timeout reached, vm not running")

@pytest.fixture
def verify_vm_stopped(mgmt_sys_api_clients, provider, vm_name):
    '''
        Verifies the vm is in the stopped state for the test.  Uses calls to the actual provider api.  
          It will stop the vm if necessary.

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :param vm_name: name of the vm 
        :type  vm_name: str
        :return: None
        :rtype: None 
    '''
    count = 0
    while count < 10:
        state = mgmt_sys_api_clients[provider].vm_status(vm_name)
        if DOWN_REGEX.match(state):
            return
        elif ON_REGEX.match(state):
            mgmt_sys_api_clients[provider].stop_vm(vm_name)
        elif SUSPEND_REGEX.match(state):
            mgmt_sys_api_clients[provider].start_vm(vm_name)
        print "Sleeping 15secs...(current state: " + \
                state + ", needed state: stopped)"
        time.sleep(15)
        count += 1
    raise Exception("timeout reached, vm not running")

@pytest.fixture
def verify_vm_suspended(mgmt_sys_api_clients, provider, vm_name):
    '''
        Verifies the vm is in the suspended state for the test.  Uses calls to the actual provider api.  
          It will start and suspend the vm if necessary.

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :param vm_name: name of the vm 
        :type  vm_name: str
        :return: None
        :rtype: None
    '''
    count = 0
    while count < 10:
        state = mgmt_sys_api_clients[provider].vm_status(vm_name)
        if SUSPEND_REGEX.match(state):
            return
        elif ON_REGEX.match(state):
            mgmt_sys_api_clients[provider].suspend_vm(vm_name)
        elif ON_REGEX.match(state):
            mgmt_sys_api_clients[provider].start_vm(vm_name)
        print "Sleeping 15secs...(current state: " + \
                state + ", needed state: suspended)"
        time.sleep(15)
        count += 1
    raise Exception("timeout reached, vm not running")

@pytest.fixture()
def load_providers_cluster_list(
        cfme_data,
        infra_providers_pg,
        provider):
    '''
        Load the cluster list of a specific provider.  

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :return: page for cluster list
        :rtype: Infrastructure.Clusters
    '''
    provider_details = infra_providers_pg.load_provider_details(
            provider["name"])
    return provider_details.all_clusters()

@pytest.fixture()
def load_providers_datastore_list(
        cfme_data,
        infra_providers_pg,
        provider):
    '''
        Load the cluster list of a specific provider.  

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :return: page for cluster list
        :rtype: Infrastructure.Datastores
    '''
    provider_details = infra_providers_pg.load_provider_details(
            provider["name"])
    return provider_details.all_datastores()

@pytest.fixture()
def load_providers_host_list(
        cfme_data,
        infra_providers_pg,
        provider):
    '''
        Load the host list of a specific provider.  

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :return: page for host list
        :rtype: Infrastructure.Hosts
    '''
    provider_details = infra_providers_pg.load_provider_details(
            provider["name"])
    return provider_details.all_hosts()

@pytest.fixture()
def load_providers_template_list(
        cfme_data,
        infra_providers_pg,
        provider,
        vm_name=None):
    '''
        Load the template list of a specific provider.  Will also find the page for a specific vm if name is passed

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :param vm_name: name of the vm to be started
        :type  vm_name: str
        :return: page for vm list
        :rtype: Services.VirtualMachines
    '''
    provider_details = infra_providers_pg.load_provider_details(
            cfme_data.data["management_systems"][provider]["name"])
    return provider_details.all_templates()
    