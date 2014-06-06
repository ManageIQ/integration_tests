#!/usr/bin/env python2

import argparse
import datetime

#RHEVM
from ovirtsdk.api import API

#VSPHERE
from psphere.client import Client
from psphere.managedobjects import VirtualMachine

#RHOS
from novaclient.v1_1 import client as novaclient

from utils.conf import cfme_data
from utils.conf import credentials
from utils.wait import wait_for


TIME_NOW = datetime.datetime.now()
SEC_IN_DAY = 86400


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--rhevm-use-start-time', dest='rhevm_use_start_time',
                        action='store_true', help='Use start time instead of creation time')
    parser.add_argument('--run-time', dest='run_time',
                        help='Max run time for the vms (in days)',
                        default=1)
    parser.add_argument('--text', dest='text',
                        help='Text in the name of vm to be affected',
                        default='test_')
    args = parser.parse_args()
    return args


def rhevm_create_api(url, username, password):
    """Creates rhevm api endpoint.

    Args:
        url: URL to rhevm provider
        username: username used to log in into rhevm
        password: password used to log in into rhevm
    """
    apiurl = 'https://%s:443/api' % url
    return API(url=apiurl, username=username, password=password, insecure=True,
               persistent_auth=False)


def vsphere_create_api(url, username, password):
    """Creates vsphere api endpoint.

    Args:
        url: URL to vsphere provider
        username: username used to log in into vsphere
        password: password used to log in into vsphere
    """
    return Client(server=url, username=username, password=password)


def rhos_create_api(auth_url, username, password, project_id):
    """Creates rhos api endpoint.

    Args:
        auth_url: authentication URL of the rhos provider
        username: username used to log in into rhos
        password: password used to log in into rhos
        project_id: name of the relevant project in rhos
    """
    return novaclient.Client(username, password, project_id, auth_url, service_type='compute')


def rhevm_vm_status(api, vm_name):
    """Returns status message of VM on rhevm.

    Args:
        api: api endpoint to rhevm
        vm_name: name of the vm
    """
    vm = api.vms.get(vm_name)
    return vm.get_status().state


def rhevm_is_vm_up(api, vm_name):
    """Returns True if VM on rhevm is up.

    Args:
        api: api endpoint to rhevm
        vm_name: name of the vm
    """
    vm = api.vms.get(vm_name)
    if vm.get_status().state == 'up':
        return True
    return False


def vsphere_is_vm_up(api, vm_name):
    """Returns True if VM on vsphere is up.

    Args:
        api: api endpoint to vsphere
        vm_name: name of the vm
    """
    vm = VirtualMachine.get(api, name=vm_name)
    if vm.runtime.powerState == 'poweredOn':
        return True
    return False


def rhevm_is_vm_down(api, vm_name):
    """Returns True if VM on rhevm is down.

    Args:
        api: api endpoint to rhevm
        vm_name: name of the vm
    """
    vm = api.vms.get(vm_name)
    if vm.get_status().state == 'down':
        return True
    return False


def vsphere_is_vm_down(api, vm_name):
    """Returns True if VM on vsphere is down.

    Args:
        api: api endpoint to vsphere
        vm_name: name og the vm
    """
    vm = VirtualMachine.get(api, name=vm_name)
    if vm.runtime.powerState == 'poweredOff':
        return True
    return False


def rhevm_delete_vm(api, vm_name):
    """Deletes VM from rhevm-type provider.
    If needed, stops the VM first, then deletes it.

    Args:
        api: api endpoint to rhevm
        vm_name: name of the vm
    """
    vm = api.vms.get(vm_name)
    if not rhevm_is_vm_down(api, vm_name):
        if not rhevm_is_vm_up(api, vm_name):
            #something is wrong, locked image etc
            print "Something went wrong with %s" % vm_name
            print "Skipping this vm..."
            return
        print "Powering down: %s" % vm.get_name()
        vm.stop()
        try:
            wait_for(rhevm_is_vm_down, [api, vm_name], fail_condition=False, delay=10, num_sec=120)
        except Exception, e:
            print str(e)
            print "Trying to continue..."
            return
    print "Deleting: %s" % vm.get_name()
    vm.delete()


def vsphere_delete_vm(api, vm_name):
    """Deletes VM from vsphere-type provider.
    If needed, stops the VM first, then deletes it.

    Args:
        api: api endpoint to vsphere
        vm_name: name of the vm
    """
    vm = VirtualMachine.get(api, name=vm_name)
    if not rhevm_is_vm_down(api, vm_name):
        if not rhevm_is_vm_up(api, vm_name):
            print "Something went wrong with %s" % vm_name
            print "Skipping this vm..."
            return
        print "Powering down: %s" % vm.name
        vm.PowerOffVM_Task()
        try:
            wait_for(vsphere_is_vm_down, [api, vm_name], fail_condition=False, delay=10,
                     num_sec=120)
        except Exception, e:
            print str(e)
            print "Trying to continue..."
    print "Deleting: %s" % vm.name
    vm.Destroy_Task()


def is_affected(vm_name, text):
    """Returns True if name of the vm contains certain text.

    Args:
        vm_name: name of the vm
        text: string to look for in the name of the vm
    """
    if text in vm_name:
        return True
    return False


def rhevm_check_with_api(api, rhevm_use_start_time, run_time, text):
    """Uses api to perform checking of vms on rhevm-type provider.

    Args:
        api: api endpoint to rhevm
        rhevm_use_start_time: indicates to use start time instead of creation time of the vm
        run_time: when this run time is exceeded for the VM, it will be deleted
        text: when this string is found in the name of VM, it may be deleted
    """
    vms = api.vms.list()
    for vm in vms:
        vm_name = vm.get_name()
        if not rhevm_use_start_time:
            creation_time = vm.get_creation_time()
            crt = creation_time.replace(tzinfo=None)
            runtime = TIME_NOW - crt
            if runtime.days >= run_time and is_affected(vm_name, text):
                print "%s runtime: %s" % (vm_name, runtime.days)
                rhevm_delete_vm(api, vm_name)
        else:
            if rhevm_is_vm_up(api, vm_name):
                start_time = vm.get_start_time()
                stt = start_time.replace(tzinfo=None)
                runtime = TIME_NOW - stt
                if runtime.days >= run_time and is_affected(vm_name, text):
                    print "%s runtime: %s" % (vm_name, runtime.days)
                    rhevm_delete_vm(api, vm_name)


def vsphere_check_with_api(api, run_time, text):
    """Uses api to perform checking of vms on vsphere-type provider.

    Args:
        api: api endpoint to vsphere
        run_time: when this run time is exceeded for the VM, it will be deleted
        text: when this string is found in the name of VM, it may be deleted
    """
    vms = VirtualMachine.all(api)
    for vm in vms:
        vm_name = vm.name
        running_for = vm.summary.quickStats.uptimeSeconds / SEC_IN_DAY
        if running_for >= run_time and is_affected(vm_name, text):
            print "%s runtime: %s" % (vm_name, running_for)
            vsphere_delete_vm(api, vm_name)


def rhos_check_with_api(api, run_time, text):
    """Uses api to perform checking of vms on rhos-type provider.

    Args:
        api: api endpoint to rhos
        run_time: when this run time is exceeded for the VM, it will be deleted
        text: when this string is found in the name of VM, it may be deleted
    """
    vms = api.servers.list()
    for vm in vms:
        vm_name = vm.name
        created = vm.created
        sep_year = created.find('-')
        sep_month = created.find('-', sep_year+1)
        sep_day = created.find('T')
        sep_hour = created.find(':')
        sep_minute = created.find(':', sep_hour+1)
        sep_second = created.find('Z')
        year = int(created[:sep_year])
        month = int(created[sep_year+1:sep_month])
        day = int(created[sep_month+1:sep_day])
        hour = int(created[sep_day+1:sep_hour])
        minute = int(created[sep_hour+1:sep_minute])
        second = int(created[sep_minute+1:sep_second])
        vm_time = datetime.datetime(year, month, day, hour, minute, second)
        runtime = TIME_NOW - vm_time
        if runtime.days >= run_time and is_affected(vm_name, text):
            print "%s runtime: %s" % (vm_name, runtime.days)
            print "Deleting: %s" % vm.name
            vm.delete()


if __name__ == "__main__":
    args = parse_cmd_line()

    providers = cfme_data['management_systems']

    for provider in providers:
        print "=== Starting provider %s ===" % provider
        if 'rhevm' in providers[provider]['type']:
            rhevm_credentials = providers[provider]['credentials']
            rhevm_url = providers[provider]['hostname']
            rhevm_username = credentials[rhevm_credentials]['username']
            rhevm_password = credentials[rhevm_credentials]['password']
            try:
                rhevm_api = rhevm_create_api(rhevm_url, rhevm_username, rhevm_password)
                rhevm_check_with_api(rhevm_api, args.rhevm_use_start_time, args.run_time, args.text)
            except Exception, e:
                print str(e)
                print "Skipping this provider..."
        if 'virtualcenter' in providers[provider]['type']:
            vsphere_credentials = providers[provider]['credentials']
            vsphere_url = providers[provider]['hostname']
            vsphere_username = credentials[vsphere_credentials]['username']
            vsphere_password = credentials[vsphere_credentials]['password']
            try:
                vsphere_api = vsphere_create_api(vsphere_url, vsphere_username, vsphere_password)
                vsphere_check_with_api(vsphere_api, args.run_time, args.text)
            except Exception, e:
                print str(e)
                print "Skipping this provider..."
        if 'openstack' in providers[provider]['type']:
            rhos_auth_url = providers[provider]['auth_url']
            rhos_credentials = providers[provider]['credentials']
            rhos_username = credentials[rhos_credentials]['username']
            rhos_password = credentials[rhos_credentials]['password']
            rhos_project_id = credentials[rhos_credentials]['tenant']
            try:
                rhos_api = rhos_create_api(rhos_auth_url, rhos_username, rhos_password,
                                           rhos_project_id)
                rhos_check_with_api(rhos_api, args.run_time, args.text)
            except Exception, e:
                print str(e)
                print "Skipping this provider..."
        print "=== End of provider %s ===" % provider
