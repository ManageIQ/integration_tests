""" Base module for Management Systems classes. """

import time
import re
from abc import ABCMeta, abstractmethod

import boto
from pysphere import *
from pysphere.resources.vi_exception import VIException
from pysphere.resources import VimService_services as VI
from pysphere.vi_task import VITask
from ovirtsdk.api import API


class MgmtSystemAPIBase(object):
    """ Base interface class for Management Systems. """
    __metaclass__ = ABCMeta

    @abstractmethod
    def start_vm(self, vm_name):
        """
            Starts a vm.

            :param vm_name: name of the vm to be started
            :type  vm_name: str
            :return: whether vm action has been initiated properly
            :rtype: boolean
        """
        raise NotImplementedError('start_vm not implemented.')

    @abstractmethod
    def stop_vm(self, vm_name):
        """
            Stops a vm.

            :param vm_name: name of the vm to be stopped
            :type  vm_name: str
            :return: whether vm action has been initiated properly
            :rtype: boolean
        """
        raise NotImplementedError('stop_vm not implemented.')

    @abstractmethod
    def create_vm(self, vm_name):
        """
            Creates a vm.

            :param vm_name: name of the vm to be created
            :type  vm_name: str
            :return: whether vm action has been initiated properly
            :rtype: boolean
        """
        raise NotImplementedError('create_vm not implemented.')

    @abstractmethod
    def delete_vm(self, vm_name):
        """
            Deletes a vm.

            :param vm_name: name of the vm to be deleted
            :type  vm_name: str
            :return: whether vm action has been initiated properly
            :rtype: boolean
        """
        raise NotImplementedError('delete_vm not implemented.')

    @abstractmethod
    def restart_vm(self, vm_name):
        """
            Restart a vm.

            :param vm_name: name of the vm to be restarted
            :type  vm_name: str
            :return: whether vm stop/start have been initiated properly
            :rtype: boolean
        """
        raise NotImplementedError('restart_vm not implemented.')

    @abstractmethod
    def list_vm(self, **kwargs):
        """
            Returns a list of vm names.

            :return: list of vm names
            :rtype: list
        """
        raise NotImplementedError('list_vm not implemented.')

    @abstractmethod
    def info(self):
        """
            Returns basic information about the mgmt system.

            :return: string representation of name/version of mgmt system.
            :rtype: str
        """
        raise NotImplementedError('info not implemented.')

    @abstractmethod
    def disconnect(self):
        """
            Disconnect the API from mgmt system.
        """
        raise NotImplementedError('disconnect not implemented.')

    @abstractmethod
    def vm_status(self, vm_name):
        """
            Status of VM.

            :param vm_name: name of the vm to get status
            :type  vm_name: str
            :return: state of the vm
            :rtype: string
        """
        raise NotImplementedError('vm_status not implemented.')

    @abstractmethod
    def is_vm_running(self, vm_name):
        """
            Is the vm running?

            :param vm_name: name of the vm
            :type  vm_name: str
            :return: whether the vm is running or not
            :rtype: boolean
        """
        raise NotImplementedError('is_vm_running not implemented.')

    @abstractmethod
    def is_vm_stopped(self, vm_name):
        """
            Is the vm stopped?

            :param vm_name: name of the vm
            :type  vm_name: str
            :return: whether the vm is stopped or not
            :rtype: boolean
        """
        raise NotImplementedError('is_vm_stopped not implemented.')

    @abstractmethod
    def is_vm_suspended(self, vm_name):
        """
            Is the vm suspended?

            :param vm_name: name of the vm
            :type  vm_name: str
            :return: whether the vm is suspended or not
            :rtype: boolean
        """
        raise NotImplementedError('is_vm_suspended not implemented.')

    @abstractmethod
    def suspend_vm(self, vm_name):
        """
            Suspend a vm.

            :param vm_name: name of the vm to be suspended
            :type  vm_name: str
            :return: whether vm suspend has been initiated properly
            :rtype: boolean
        """
        raise NotImplementedError('restart_vm not implemented.')

    @abstractmethod
    def clone_vm(self, source_name, vm_name):
        """
            Clone a VM.

            :param source_name: The source VM to clone from
            :type  source_name: str
            :param vm_name: The name of the new VM
            :type  vm_name: str
            :return: IP address of the clone
            :rtype: str
        """
        raise NotImplementedError('clone_vm not implemented.')

class VMWareSystem(MgmtSystemAPIBase):
    """
    Client to Vsphere API

    This class piggy backs off pysphere.

    Benefits of pysphere:
      - Don't need intimate knowledge w/ vsphere api itself.
    Detriments of pysphere:
      - Response often are not detailed enough.
    """

    def __init__(self, hostname='localhost', username='root', password='rootpwd'):
        """ Initialize VMWareSystem """
        # sanitize hostname
        if hostname.startswith('https://'):
            hostname.replace('https://', '')
        elif hostname.startswith('http://'):
            hostname.replace('http://', '')

        if hostname.endswith('/api'):
            hostname.replace('/api', '')

        self.api = VIServer()
        self.api.connect(hostname, username, password)

    def _get_vm(self, vm_name=None):
        """ VMWareSystem implementation in _get_vm. """
        if vm_name is None:
            raise Exception('Could not find a VM named %s.' % vm_name)
        else:
            try:
                vm = self.api.get_vm_by_name(vm_name)
                return vm
            except VIException as ex:
                raise Exception(ex)

    def _get_resource_pool(self, resource_pool_name=None):
        rps = self.api.get_resource_pools()
        for mor, path in rps.iteritems():
            if re.match('.*%s' % resource_pool_name,path):
                return mor
        # Just pick the first
        return rps.keys()[0]

    def _find_ip(self, vm, ipv6=False):
        maxwait = 120
        net_info = None
        waitcount = 0
        while net_info is None:
            if waitcount > maxwait:
                break
            net_info = vm.get_property('net',False)
            waitcount += 5
            time.sleep(5)
        if net_info:
            for ip in net_info[0]['ip_addresses']:
                if ipv6 and re.match(r'\d{1,4}\:.*',ip) and not re.match('fe83\:.*',ip):
                    return ip
                elif not ipv6 and re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',ip) and ip != '127.0.0.1':
                    return ip
        return None

    def start_vm(self, vm_name):
        """ VMWareSystem implementation of start_vm. """
        vm = self._get_vm(vm_name)
        if vm.is_powered_on():
            raise Exception('Could not start %s because it\'s already running.' % vm_name)
        else:
            vm.power_on()
            ack = vm.get_status()
            if ack == 'POWERED ON':
                return True
        return False

    def stop_vm(self, vm_name):
        """ VMWareSystem implementation of stop_vm. """
        vm = self._get_vm(vm_name)
        if vm.is_powered_off():
            raise Exception('Could not stop %s because it\'s not running.' % vm_name)
        else:
            vm.power_off()
            ack = vm.get_status()
            if ack == 'POWERED OFF':
                return True
        return False

    def delete_vm(self, vm_name):
        """ VMWareSystem implementation of delete_vm. """
        vm = self._get_vm(vm_name)

        if vm.is_powered_on():
            raise Exception('Could not stop %s because it\'s still running.' % vm_name)
        else:
            # When pysphere moves up to 0.1.8, we can just do:
            # vm.destroy()
            request = VI.Destroy_TaskRequestMsg()
            _this = request.new__this(vm._mor)
            _this.set_attribute_type(vm._mor.get_attribute_type())
            request.set_element__this(_this)
            rtn = self.api._proxy.Destroy_Task(request)._returnval

            task = VITask(rtn, self.api)
            status = task.wait_for_state([task.STATE_SUCCESS, task.STATE_ERROR])
            if status == task.STATE_SUCCESS:
                return True
        return False

    def create_vm(self, vm_name):
        """ VMWareSystem implementation of create_vm. """
        #Unfortunately, there are not enough smurf slaves in the village to build this functionality yet.
        pass

    def restart_vm(self, vm_name):
        """ VMWareSystem implementation of restart_vm. """
        if not self.stop_vm(vm_name):
            return False
        else:
            return self.start_vm(vm_name)

    def list_vm(self, **kwargs):
        """ VMWareSystem implementation of list_vm. """
        vm_list = self.api.get_registered_vms(**kwargs)
        return [vm.split(']', 1)[-1].strip() for vm in vm_list]

    def info(self):
        """ VMWareSystem implementation of info. """
        return '%s %s' % (self.api.get_server_type(), self.api.get_api_version())

    def disconnect(self):
        """ VMWareSystem implementation of disconnect. """
        self.api.disconnect()

    def vm_status(self, vm_name):
        """ VMWareSystem implementation of vm.get_status """
        state = self._get_vm(vm_name).get_status()
        print "vm " + vm_name + " status is " + state
        return state

    def is_vm_running(self, vm_name):
        """ VMWareSystem implementation of is_vm_running. """
        state = self.vm_status(vm_name)
        return "POWERED ON" == state

    def is_vm_stopped(self, vm_name):
        """ VMWareSystem implementation of is_vm_stopped. """
        state = self.vm_status(vm_name)
        return "POWERED OFF" == state

    def is_vm_suspended(self, vm_name):
        """ VMWareSystem implementation of is_vm_suspended. """
        state = self.vm_status(vm_name)
        return "SUSPENDED" == state

    def suspend_vm(self, vm_name):
        """ VMWareSystem implementation of suspend_vm. """
        vm = self._get_vm(vm_name)
        if vm.is_powered_off():
            raise Exception('Could not suspend %s because it\'s not running.' % vm_name)
        else:
            vm.suspend()
            return vm.get_status()

    def clone_vm(self, source_name, vm_name, resourcepool=None):
        """ VMWareSystem implementation of clone_vm. """
        vm = self._get_vm(source_name)
        if vm:
            clone = vm.clone(vm_name, sync_run=True, resourcepool=self._get_resource_pool(resourcepool))
            return self._find_ip(clone)
        else:
            raise Exception('Could not clone %s' % source_name)

class RHEVMSystem(MgmtSystemAPIBase):
    """
    Client to RHEVM API

    This class piggy backs off ovirtsdk.

    Benefits of ovirtsdk:
    - Don't need intimite knowledge w/ RHEVM api itself.
    Detriments of ovirtsdk:
    - Response to most quaries are returned as an object rather than a string.
      This makes it harder to do simple stuff like getting the status of a vm.
    - Because of this, it makes listing VMs based on **kwargs impossible
      since ovirtsdk relies on re class to find matches.

    I.E. List out VM with this name (positive case)
      Ideal: self.api.vms.list(name='test_vm')
      Underneath the hood:
        - ovirtsdk fetches list of all vms [ovirtsdk.infrastructure.brokers.VM
          object, ...]
        - ovirtsdk then tries to filter the result using re.
          - tries to look for 'name' attr in ovirtsdk.infrastructure.brokers.VM
            object
          - found name attribute, in this case, the type of the value of the
            attribute is string.
          - match() succeed in comparing the value to 'test_vm'

    I.E. List out VM with that's powered on (negative case)
      Ideal: self.api.vms.list(status='up')
      Underneath the hood:
        - '^same step as above except^'
            - found status attribute, in this case, the type of the value of
              the attribute is ovirtsdk.xml.params.Status
            - match() failed because class is compared to string 'up'

     This problem should be attributed to how RHEVM api was designed rather
     than how ovirtsdk handles RHEVM api responses.

    - Obj. are not updated after action calls.
      - I.E.
        vm = api.vms.get(name='test_vm')
        vm.status.get_state() # returns 'down'
        vm.start()
        # wait a few mins
        vm.status.get_state() # returns 'down'; wtf?

        vm = api.vms.get(name='test_vm')
        vm.status.get_state() # returns 'up'
    """

    def __init__(self, hostname='localhost', username='root', password='rootpwd'):
        """ Initialize RHEVMSystem """
        # sanitize hostname
        if not hostname.startswith('https://'):
            hostname = 'https://%s' % hostname
        if not hostname.endswith('/api'):
            hostname = '%s/api' % hostname

        self.api = API(url=hostname, username=username, password=password, insecure=True)

    def _get_vm(self, vm_name=None):
        """ RHEVMSystem implementation in _get_vm. """
        if vm_name is None:
            raise Exception('Could not find a VM named %s.' % vm_name)
        else:
            vm = self.api.vms.get(name=vm_name)
            if vm is None:
                raise Exception('Could not find a VM named %s.' % vm_name)
            return vm

    def start_vm(self, vm_name=None):
        """ RHEVMSystem implementation of start_vm. """
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            raise Exception('Could not start %s because it\'s already running.' % vm_name)
        else:
            ack = vm.start()
            if ack.get_status().get_state() == 'complete':
                return True
        return False

    def stop_vm(self, vm_name):
        """ RHEVMSystem implementation of stop_vm. """
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            raise Exception('Could not stop %s because it\'s not running.' % vm_name)
        else:
            ack = vm.stop()
            if ack.get_status().get_state() == 'complete':
                return True
        return False

    def delete_vm(self, vm_name):
        """ RHEVMSystem implementation of delete_vm. """
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            raise Exception('Could not delete %s because it\'s still running.' % vm_name)
        else:
            ack = vm.delete()
            if ack.get_status().get_state() == '':
                return True
        return False

    def create_vm(self, vm_name):
        """ RHEVMSystem implementation of create_vm. """
        #Unfortunately, there are not enough smurf slaves in the village to build this functionality yet.
        pass

    def restart_vm(self, vm_name):
        """ RHEVMSystem implementation of restart_vm. """
        if not self.stop_vm(vm_name):
            return False
        else:
            return self.start_vm(vm_name)

    def list_vm(self, **kwargs):
        """ RHEVMSystem implementation of list_vm. """
        # list vm based on kwargs can be buggy
        # i.e. you can't return a list of powered on vm
        # but you can return a vm w/ a matched name
        vm_list = self.api.vms.list(**kwargs)
        return [vm.name for vm in vm_list]

    def info(self):
        """ RHEVMSystem implementation of info. """
        # and we got nothing!
        pass

    def disconnect(self):
        """ RHEVMSystem implementation of disconnect. """
        self.api.disconnect()

    def vm_status(self, vm_name=None):
        """ RHEVMSystem implementation of vm_status. """
        state = self._get_vm(vm_name).get_status().get_state()
        print "vm " + vm_name + " status is " + state
        return state

    def is_vm_running(self, vm_name):
        """ RHEVMSystem implementation of is_vm_running. """
        state = self.vm_status(vm_name)
        return "up" == state

    def is_vm_stopped(self, vm_name):
        """ RHEVMSystem implementation of is_vm_stopped. """
        state = self.vm_status(vm_name)
        return "down" == state

    def is_vm_suspended(self, vm_name):
        """ RHEVMSystem implementation of is_vm_suspended. """
        state = self.vm_status(vm_name)
        return "suspended" == state

    def suspend_vm(self, vm_name):
        """ RHEVMSystem implementation of suspend_vm. """
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            raise Exception('Could not suspend %s because it\'s not running.' % vm_name)
        else:
            ack = vm.suspend()
            return ack.get_status().get_state() == 'complete'

    def clone_vm(self, source_name, vm_name):
        """ RHEVMSystem implementation of clone_vm. """
        pass


class EC2System(MgmtSystemAPIBase):
    """EC2 Management System, powered by boto

    Wraps the EC2 API and mimics the behavior of other implementors of
    MgmtServiceAPIBase for us in VM control testing

    Instead of username and password, accepts access_key_id and
    secret_access_key, the AWS analogs to those ideas. These are passed, along
    with any kwargs, straight through to boto's EC2 connection factory. This
    allows customization of the EC2 connection, to connect to another region,
    for example.

    For the purposes of the EC2 system, a VM's instance ID is its name because
    EC2 instances don't have to have unique names.

    """

    states = {
        'running': ('running',),
        'stopped': ('stopped', 'terminated'),
        'suspended': (),
        'deleted': ('terminated',),
    }

    def __init__(self, access_key_id, secret_access_key, **kwargs):
        self.api = boto.connect_ec2(access_key_id, secret_access_key, **kwargs)

    def disconnect(self):
        """Disconnect from the EC2 API -- NOOP

        AWS EC2 service is stateless, so there's nothing to disconnect from
        """
        pass

    def info(self):
        """Returns the current versions of boto and the EC2 API being used"""
        return '%s %s' % (boto.UserAgent, self.api.APIVersion)

    def list_vm(self):
        """Returns a list from instance IDs currently known to EC2"""
        return [instance.id for instance in self._get_all_instances()]

    def vm_status(self, instance_id):
        """Returns the status of the requested instance

        :param  instance_id: ID of the instance to inspect
        :type   instance_id: basestring
        :return: Instance status.
        :rtype:  basestring

        See this page for possible return values:
        http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-ItemType-InstanceStateType.html

        """
        instance_id = self._get_instance_id_by_name(instance_id)
        reservations = self.api.get_all_instances([instance_id])
        instances = self._get_instances_from_reservations(reservations)
        for instance in instances:
            if instance.id == instance_id:
                return instance.state

    def create_vm(self, ami_id, *args, **kwargs):
        """Instantiate the requested VM image

        :param  ami_id: AMI ID to instantiate
        :type   ami_id: basestring
        :return: Instance ID of the created instance
        :rtype:  basestring

        Packed arguments are passed along to boto's run_instances method.

        min_count and max_count will be forced to '1'; if you're trying to do
        anything fancier than that, you might be in the wrong place

        """
        # Enforce create_vm only creating one VM
        kwargs.update({
            'min_count': 1,
            'max_count': 1,
        })
        reservation = self.api.run_instances(ami_id, *args, **kwargs)
        instances = self._get_instances_from_reservations([reservation])
        # Should have only made one VM; return its ID for use in other methods
        return instances[0].id

    def delete_vm(self, instance_id):
        """Deletes the an instance

        :param  instance_id: ID of the instance to act on
        :type   instance_id: basestring
        :return: Whether or not the backend reports the action completed
        :rtype:  bool

        """
        instance_id = self._get_instance_id_by_name(instance_id)
        try:
            self.api.terminate_instances([instance_id])
            self._block_until(instance_id, self.states['deleted'])
            return True
        except ActionTimedOutError:
            return False

    def start_vm(self, instance_id):
        """Start an instance

        :param  instance_id: ID of the instance to act on
        :type   instance_id: basestring
        :return: Whether or not the backend reports the action completed
        :rtype:  bool

        """
        instance_id = self._get_instance_id_by_name(instance_id)
        try:
            self.api.start_instances([instance_id])
            self._block_until(instance_id, self.states['running'])
            return True
        except ActionTimedOutError:
            return False

    def stop_vm(self, instance_id):
        """Stop an instance

        :param  instance_id: ID of the instance to act on
        :type   instance_id: basestring
        :return: Whether or not the backend reports the action completed
        :rtype:  bool

        """
        instance_id = self._get_instance_id_by_name(instance_id)
        try:
            self.api.stop_instances([instance_id])
            self._block_until(instance_id, self.states['stopped'])
            return True
        except ActionTimedOutError:
            return False

    def restart_vm(self, instance_id):
        """Restart an instance

        :param  instance_id: ID of the instance to act on
        :type   instance_id: basestring
        :return: Whether or not the backend reports the action completed
        :rtype:  bool

        The action is taken in two separate calls to EC2. A 'False' return can
        indicate a failure of either the stop action or the start action.
        """
        # There is a reboot_instances call available on the API, but it provides
        # less insight than blocking on stop_vm and start_vm. Furthermore,
        # there is no "rebooting" state, so there are potential monitoring
        # issues that are avoided by completing these steps atomically
        return self.stop_vm(instance_id) and self.start_vm(instance_id)

    def is_vm_running(self, instance_id):
        """Is the VM running?

        :param  instance_id: ID of the instance to inspect
        :type   instance_id: basestring
        :return: Whether or not the requested instance is running
        :rtype: bool

        """
        return self.vm_status(instance_id) in self.states['running']

    def is_vm_stopped(self, instance_id):
        """Is the VM stopped?

        :param  instance_id: ID of the instance to inspect
        :type   instance_id: basestring
        :return: Whether or not the requested instance is stopped
        :rtype: bool

        """
        return self.vm_status(instance_id) in self.states['stopped']

    def suspend_vm(self, instance_id):
        """Suspend a VM: Unsupported by EC2

        :param  instance_id: ID of the instance to act on
        :type   instance_id: basestring
        :raises: Exception

        The action is taken in two separate calls to EC2. A 'False' return can
        indicate a failure of either the stop action or the start action.

        """
        raise Exception('Requested action is not supported by this system')

    def is_vm_suspended(self, instance_id):
        """Is the VM suspended? We'll never know because EC2 don't support this.

        :param  instance_id: ID of the instance to inspect
        :type   instance_id: basestring
        :raises: Exception

        """
        raise Exception('Requested action is not supported by this system')

    def clone_vm(self, source_name, vm_name):
        """ EC2System implementation of clone_vm. """
        pass

    def _get_instance_id_by_name(self, instance_name):
        # Quick validation that the instance name isn't actually an ID
        # If people start naming their instances in such a way to break this,
        # check, that would be silly, but we can upgrade to regex if necessary.
        if instance_name.startswith('i-') and len(instance_name) == 10:
            # This is already an instance id, return it!
            return instance_name

        # Filter by the 'Name' tag
        filters = {
            'tag:Name': instance_name,
        }
        reservations = self.api.get_all_instances(filters=filters)
        instances = self._get_instances_from_reservations(reservations)
        if not instances:
            raise Exception('Instance with name "%s" not found.' % instance_name)
        elif len(instances) > 1:
            raise Exception('Instance name "%s" is not unique' % instance_name)
        else:
            # We have an instance! return its ID
            return instances[0].id

    def _get_instances_from_reservations(self, reservations):
        """Takes a sequence of reservations and returns their instances"""
        instances = list()
        for reservation in reservations:
            for instance in reservation.instances:
                instances.append(instance)
        return instances

    def _get_all_instances(self):
        """Gets all instances that EC2 can see"""
        reservations = self.api.get_all_instances()
        instances = self._get_instances_from_reservations(reservations)
        return instances

    def _block_until(self, instance_id, expected, timeout=90):
        """Blocks until the given instance is in one of the expected states

        Takes an optional timeout value; set this to None to disable the timeout
        (probably a bad idea). The timeout has a sane default.

        """
        start = time.time()
        while self.vm_status(instance_id) not in expected:
            if timeout is not None and time.time() - start > timeout:
                raise ActionTimedOutError
            time.sleep(3)


class ActionTimedOutError(Exception):
    pass

