#!/usr/bin/env python2

import argparse
import datetime
import re
import sys

# RHEVM
from ovirtsdk.api import API

# VSPHERE
from psphere.client import Client
from psphere.managedobjects import VirtualMachine

# RHOS
from novaclient.v1_1 import client as novaclient

# utils
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


def vsphere_vm_status(api, vm_name):
    vm = VirtualMachine.get(api, name=vm_name)
    return vm.runtime.powerState


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
    vm_status = rhevm_vm_status(api, vm_name)
    if vm_status != 'up' and vm_status != 'down':
        # something is wrong, locked image etc
        exc_msg = "VM status: %s" % vm_status
        raise Exception(exc_msg)
    if vm_status == "up":
        print "Powering down: %s" % vm.get_name()
        vm.stop()
        wait_for(rhevm_is_vm_down, [api, vm_name], fail_condition=False, delay=10, num_sec=120)
    print "Deleting: %s" % vm_name
    vm.delete()


def vsphere_delete_vm(api, vm_name):
    """Deletes VM from vsphere-type provider.
    If needed, stops the VM first, then deletes it.

    Args:
        api: api endpoint to vsphere
        vm_name: name of the vm
    """
    vm = VirtualMachine.get(api, name=vm_name)
    vm_status = vsphere_vm_status(api, vm_name)
    if vm_status != 'poweredOn' and vm_status != 'poweredOff':
        #something is wrong, locked image etc
        exc_msg = "VM status: %s" % vm_status
        raise Exception(exc_msg)
    if vm_status == "up":
        print "Powering down: %s" % vm.name
        vm.PowerOffVM_Task()
        wait_for(vsphere_is_vm_down, [api, vm_name], fail_condition=False, delay=10,
                 num_sec=120)
    print "Deleting: %s" % vm_name
    vm.Destroy_Task()


def rhos_delete_vm(api, vm_name):
    vms = api.servers.list()
    for vm in vms:
        if vm.name == vm_name:
            print "Deleting: %s" % vm_name
            vm.delete()


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
    vms_to_delete = []
    for vm in vms:
        vm_name = vm.get_name()
        if not rhevm_use_start_time:
            creation_time = vm.get_creation_time()
            crt = creation_time.replace(tzinfo=None)
            runtime = TIME_NOW - crt
            if runtime.days >= run_time and is_affected(vm_name, text):
                print "To delete: %s with runtime: %s" % (vm_name, runtime.days)
                vms_to_delete.append(vm_name)
        else:
            if rhevm_is_vm_up(api, vm_name):
                start_time = vm.get_start_time()
                stt = start_time.replace(tzinfo=None)
                runtime = TIME_NOW - stt
                if runtime.days >= run_time and is_affected(vm_name, text):
                    print "To delete: %s with runtime: %s" % (vm_name, runtime.days)
                    vms_to_delete.append(vm_name)
    return vms_to_delete


def vsphere_check_with_api(api, run_time, text):
    """Uses api to perform checking of vms on vsphere-type provider.

    Args:
        api: api endpoint to vsphere
        run_time: when this run time is exceeded for the VM, it will be deleted
        text: when this string is found in the name of VM, it may be deleted
    """
    vms = VirtualMachine.all(api)
    vms_to_delete = []
    for vm in vms:
        vm_name = vm.name
        running_for = vm.summary.quickStats.uptimeSeconds / SEC_IN_DAY
        if running_for >= run_time and is_affected(vm_name, text):
            print "To delete: %s with runtime: %s" % (vm_name, running_for)
            vms_to_delete.append(vm_name)
    return vms_to_delete


def rhos_check_with_api(api, run_time, text):
    """Uses api to perform checking of vms on rhos-type provider.

    Args:
        api: api endpoint to rhos
        run_time: when this run time is exceeded for the VM, it will be deleted
        text: when this string is found in the name of VM, it may be deleted
    """
    vms = api.servers.list()
    vms_to_delete = []
    for vm in vms:
        vm_name = vm.name
        created = vm.created
        pattern = re.compile(r'(\d+)-(\d+)-(\d+)\w(\d+):(\d+):(\d+)\w')
        res = pattern.findall(created)
        vm_time = datetime.datetime(int(res[0][0]), int(res[0][1]), int(res[0][2]), int(res[0][3]),
                                    int(res[0][4]), int(res[0][5]))
        runtime = TIME_NOW - vm_time
        if runtime.days >= run_time and is_affected(vm_name, text):
            print "To delete: %s with runtime: %s" % (vm_name, runtime.days)
            vms_to_delete.append(vm_name)
    return vms_to_delete


def main(args, providers):
    was_exception = False

    for provider in providers:

        if 'ec2' in providers[provider]['type']:
            continue

        print "=== Starting provider %s ===" % provider

        creds = providers[provider]['credentials']
        username = credentials[creds]['username']
        password = credentials[creds]['password']

        if 'rhevm' in providers[provider]['type']:
            rhevm_url = providers[provider]['hostname']
            # establish api
            try:
                rhevm_api = rhevm_create_api(rhevm_url, username, password)
            except Exception, e:
                print "RHEVM: Failed to establish connection. Skipping this provider..."
                print str(e)
                was_exception = True
                continue
            # check for old vms
            try:
                delete_vm_list = rhevm_check_with_api(rhevm_api, args.rhevm_use_start_time,
                                                      args.run_time, args.text)
            except Exception, e:
                print "RHEVM: Failed to check for vms using api. Skipping this provider..."
                print str(e)
                was_exception = True
                continue
            # delete old vms
            for vm_name in delete_vm_list:
                try:
                    pass
                    rhevm_delete_vm(rhevm_api, vm_name)
                except Exception, e:
                    print "RHEVM: Failed to delete vm. Skipping '%s'" % vm_name
                    print str(e)
                    was_exception = True
                    continue
        if 'virtualcenter' in providers[provider]['type']:
            vsphere_url = providers[provider]['hostname']
            # establish api
            try:
                vsphere_api = vsphere_create_api(vsphere_url, username, password)
            except Exception, e:
                "VSPHERE: Failed to establish connection. Skipping this provider..."
                print str(e)
                was_exception = True
                continue
            # check for old vms
            try:
                delete_vm_list = vsphere_check_with_api(vsphere_api, args.run_time, args.text)
            except Exception, e:
                print "VSPHERE: Failed to check for vms using api. Skipping this provider..."
                print str(e)
                was_exception = True
                continue
            # delete old vms
            for vm_name in delete_vm_list:
                try:
                    pass
                    vsphere_delete_vm(vsphere_api, vm_name)
                except Exception, e:
                    print "VSPHERE: Failed to delete vm. Skipping '%s'" % vm_name
                    print str(e)
                    was_exception = True
                    continue
        if 'openstack' in providers[provider]['type']:
            rhos_auth_url = providers[provider]['auth_url']
            rhos_project_id = credentials[creds]['tenant']
            # establish api
            try:
                rhos_api = rhos_create_api(rhos_auth_url, username, password, rhos_project_id)
            except Exception, e:
                print "RHOS: Failed to establish connection. Skipping this provider..."
                print str(e)
                was_exception = True
                continue
            # check for old vms
            try:
                delete_vm_list = rhos_check_with_api(rhos_api, args.run_time, args.text)
            except Exception, e:
                print "RHOS: Failed to check for vms using api. Skipping this provider..."
                print str(e)
                was_exception = True
                continue
            # delete old vms
            for vm_name in delete_vm_list:
                try:
                    pass
                    rhos_delete_vm(rhos_api, vm_name)
                except Exception, e:
                    print "RHOS: Failed to delete vm. Skipping '%s'" % vm_name
                    print str(e)
                    was_exception = True
                    continue

        print "=== End of provider %s ===" % provider

    return was_exception


if __name__ == "__main__":
    args = parse_cmd_line()

    providers = cfme_data['management_systems']

    sys.exit(main(args, providers))
