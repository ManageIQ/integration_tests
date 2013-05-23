import pytest
from unittestzero import Assert
import re
import time

on_regex = re.compile('up|POWERED\ ON')
down_regex = re.compile('down|POWERED\ OFF')
suspend_regex = re.compile('SUSPENDED|suspended')

@pytest.fixture()  # IGNORE:E1101
def load_providers_vm_list(cfme_data, home_page_logged_in, provider, vm_name=None):
    '''
        Load the vm list of a specific provider.  Will also find the page for a specific vm if name is passed

        :param provider: name of the provider... key from cfme_data["management_systems"]
        :type  provider: str
        :param vm_name: name of the vm to be started
        :type  vm_name: str
        :return: page for vm list
        :rtype: Services.VirtualMachines
    '''
    ms_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
    ms_details = ms_pg.load_mgmt_system_details(cfme_data.data["management_systems"][provider]["name"])
    vm_pg = ms_details.all_vms()
    if vm_name is not None:
        vm_pg.find_vm_page(vm_name, None, False, False)
    return vm_pg

@pytest.fixture()  # IGNORE:E1101
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

@pytest.fixture  # IGNORE:E1101
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
        if on_regex.match(state):
            return
        elif down_regex.match(state) or suspend_regex.match(state):
            mgmt_sys_api_clients[provider].start_vm(vm_name)
        print "Sleeping 15secs...(current state: " + state + ", needed state: running)"
        time.sleep(15)
        count += 1
    raise Exception("timeout reached, vm not running")

@pytest.fixture  # IGNORE:E1101
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
        if down_regex.match(state):
            return
        elif on_regex.match(state):
            mgmt_sys_api_clients[provider].stop_vm(vm_name)
        elif suspend_regex.match(state):
            mgmt_sys_api_clients[provider].start_vm(vm_name)
        print "Sleeping 15secs...(current state: " + state + ", needed state: stopped)"
        time.sleep(15)
        count += 1
    raise Exception("timeout reached, vm not running")

@pytest.fixture  # IGNORE:E1101
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
        if suspend_regex.match(state):
            return
        elif on_regex.match(state):
            mgmt_sys_api_clients[provider].suspend_vm(vm_name)
        elif on_regex.match(state):
            mgmt_sys_api_clients[provider].start_vm(vm_name)
        print "Sleeping 15secs...(current state: " + state + ", needed state: suspended)"
        time.sleep(15)
        count += 1
    raise Exception("timeout reached, vm not running")

