# coding: utf-8
"""Base module for Management Systems classes"""
import re
import time

import boto
from abc import ABCMeta, abstractmethod
from boto.ec2 import EC2Connection, get_region
from ovirtsdk.api import API
from pysphere import VIServer, MORTypes
from pysphere.resources import VimService_services as VI
from pysphere.resources.vi_exception import VIException
from pysphere.vi_task import VITask
from novaclient.v1_1 import client as osclient
from utils.wait import wait_for


class MgmtSystemAPIBase(object):
    """Base interface class for Management Systems

    Interface notes:
    - Initializers of subclasses must support **kwargs in their
      signtures
    - Action methods (start/stop/etc) should block until the requested
      action is complete

    """
    __metaclass__ = ABCMeta

    # Flag to indicate whether or not this MgmtSystem can suspend,
    # default True
    can_suspend = True

    @abstractmethod
    def start_vm(self, vm_name):
        """Starts a vm.

        :param vm_name: name of the vm to be started
        :type  vm_name: str
        :return: whether vm action has been initiated properly
        :rtype: boolean

        """
        raise NotImplementedError('start_vm not implemented.')

    @abstractmethod
    def stop_vm(self, vm_name):
        """Stops a vm.

        :param vm_name: name of the vm to be stopped
        :type  vm_name: str
        :return: whether vm action has been initiated properly
        :rtype: boolean

        """
        raise NotImplementedError('stop_vm not implemented.')

    @abstractmethod
    def create_vm(self, vm_name):
        """Creates a vm.

        :param vm_name: name of the vm to be created
        :type  vm_name: str
        :return: whether vm action has been initiated properly
        :rtype: boolean

        """
        raise NotImplementedError('create_vm not implemented.')

    @abstractmethod
    def delete_vm(self, vm_name):
        """Deletes a vm.

        :param vm_name: name of the vm to be deleted
        :type  vm_name: str
        :return: whether vm action has been initiated properly
        :rtype: boolean

        """
        raise NotImplementedError('delete_vm not implemented.')

    @abstractmethod
    def restart_vm(self, vm_name):
        """Restart a vm.

        :param vm_name: name of the vm to be restarted
        :type  vm_name: str
        :return: whether vm stop/start have been initiated properly
        :rtype: boolean

        """
        raise NotImplementedError('restart_vm not implemented.')

    @abstractmethod
    def list_vm(self, **kwargs):
        """Returns a list of vm names.

        :return: list of vm names
        :rtype: list

        """
        raise NotImplementedError('list_vm not implemented.')

    @abstractmethod
    def list_template(self):
        """Returns a list of templates/images.

        :return: list of template/image names
        :rtype: list

        """
        raise NotImplementedError('list_template not implemented.')

    @abstractmethod
    def list_flavor(self):
        """Returns a list of flavors.

        Only valid for OpenStack and Amazon

        :return: list of flavor names
        :rtype: list

        """
        raise NotImplementedError('list_flavor not implemented.')

    @abstractmethod
    def info(self):
        """Returns basic information about the mgmt system.

        :return: string representation of name/version of mgmt system.
        :rtype: str

        """
        raise NotImplementedError('info not implemented.')

    @abstractmethod
    def disconnect(self):
        """Disconnect the API from mgmt system"""
        raise NotImplementedError('disconnect not implemented.')

    @abstractmethod
    def vm_status(self, vm_name):
        """Status of VM.

        :param vm_name: name of the vm to get status
        :type  vm_name: str
        :return: state of the vm
        :rtype: string

        """
        raise NotImplementedError('vm_status not implemented.')

    @abstractmethod
    def is_vm_running(self, vm_name):
        """Is the vm running?

        :param vm_name: name of the vm
        :type  vm_name: str
        :return: whether the vm is running or not
        :rtype: boolean

        """
        raise NotImplementedError('is_vm_running not implemented.')

    @abstractmethod
    def is_vm_stopped(self, vm_name):
        """Is the vm stopped?

        :param vm_name: name of the vm
        :type  vm_name: str
        :return: whether the vm is stopped or not
        :rtype: boolean

        """
        raise NotImplementedError('is_vm_stopped not implemented.')

    @abstractmethod
    def is_vm_suspended(self, vm_name):
        """Is the vm suspended?

        :param vm_name: name of the vm
        :type  vm_name: str
        :return: whether the vm is suspended or not
        :rtype: boolean

        """
        raise NotImplementedError('is_vm_suspended not implemented.')

    @abstractmethod
    def suspend_vm(self, vm_name):
        """Suspend a vm.

        :param vm_name: name of the vm to be suspended
        :type  vm_name: str
        :return: whether vm suspend has been initiated properly
        :rtype: boolean

        """
        raise NotImplementedError('restart_vm not implemented.')

    @abstractmethod
    def clone_vm(self, source_name, vm_name):
        """Clone a VM.

        :param source_name: The source VM to clone from
        :type  source_name: str
        :param vm_name: The name of the new VM
        :type  vm_name: str
        :return: IP address of the clone
        :rtype: str

        """
        raise NotImplementedError('clone_vm not implemented.')


class VMWareSystem(MgmtSystemAPIBase):
    """Client to Vsphere API

    This class piggy backs off pysphere.

    Benefits of pysphere:
      - Don't need intimate knowledge w/ vsphere api itself.
    Detriments of pysphere:
      - Response often are not detailed enough.

    """

    def __init__(self, hostname, username, password, **kwargs):
        self.api = VIServer()
        self.api.connect(hostname, username, password)

    def _get_vm(self, vm_name=None):
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
            if re.match('.*%s' % resource_pool_name, path):
                return mor
        # Just pick the first
        return rps.keys()[0]

    def _find_ip(self, vm):
        maxwait = 600
        net_info = None
        waitcount = 0
        while net_info is None:
            if waitcount > maxwait:
                break
            net_info = vm.get_property('net', False)
            waitcount += 5
            time.sleep(5)
        if net_info:
            ipv4_re = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
            for ip in net_info[0]['ip_addresses']:
                if re.match(ipv4_re, ip) and ip != '127.0.0.1':
                    return ip
        return None

    def _get_list_vms(self, get_template=False):
        template_or_vm_list = []

        props = self.api._retrieve_properties_traversal(property_names=['name', 'config.template'],
                                                        from_node=None,
                                                        obj_type=MORTypes.VirtualMachine)
        for prop in props:
            vm = None
            template = None
            for elem in prop.PropSet:
                if elem.Name == "name":
                    vm = elem.Val
                elif elem.Name == "config.template":
                    template = elem.Val
            if vm is None or template is None:
                continue
            if template == bool(get_template):
                template_or_vm_list.append(vm)
        return template_or_vm_list

    def start_vm(self, vm_name):
        vm = self._get_vm(vm_name)
        if vm.is_powered_on():
            return True
        else:
            vm.power_on()
            ack = vm.get_status()
            if ack == 'POWERED ON':
                return True
        return False

    def stop_vm(self, vm_name):
        vm = self._get_vm(vm_name)
        if vm.is_powered_off():
            return True
        else:
            vm.power_off()
            ack = vm.get_status()
            if ack == 'POWERED OFF':
                return True
        return False

    def delete_vm(self, vm_name):
        vm = self._get_vm(vm_name)

        if vm.is_powered_on():
            self.stop_vm(vm_name)

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
        else:
            return False

    def create_vm(self, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')

    def restart_vm(self, vm_name):
        if not self.stop_vm(vm_name):
            return False
        else:
            return self.start_vm(vm_name)

    def list_vm(self):
        return self._get_list_vms()

    def list_template(self):
        return self._get_list_vms(get_template=True)

    def list_flavor(self):
        raise NotImplementedError('This function is not supported on this platform.')

    def list_host(self):
        return self.api.get_hosts()

    def list_datastore(self):
        return self.api.get_datastores()

    def list_cluster(self):
        return self.api.get_clusters()

    def info(self):
        return '%s %s' % (self.api.get_server_type(), self.api.get_api_version())

    def disconnect(self):
        self.api.disconnect()

    def vm_status(self, vm_name):
        state = self._get_vm(vm_name).get_status()
        print "vm " + vm_name + " status is " + state
        return state

    def is_vm_running(self, vm_name):
        state = self.vm_status(vm_name)
        return "POWERED ON" == state

    def is_vm_stopped(self, vm_name):
        state = self.vm_status(vm_name)
        return "POWERED OFF" == state

    def is_vm_suspended(self, vm_name):
        state = self.vm_status(vm_name)
        return "SUSPENDED" == state

    def suspend_vm(self, vm_name):
        vm = self._get_vm(vm_name)
        if vm.is_powered_off():
            raise Exception('Could not suspend %s because it\'s not running.' % vm_name)
        else:
            vm.suspend()
            return self.is_vm_suspended(vm_name)

    def clone_vm(self, source_name, vm_name, resourcepool=None):
        vm = self._get_vm(source_name)
        if vm:
            clone = vm.clone(vm_name, sync_run=True,
                resourcepool=self._get_resource_pool(resourcepool))
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

    E.G. List out VM with this name (positive case)
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

    E.G. List out VM with that's powered on (negative case)
      Ideal: self.api.vms.list(status='up')
      Underneath the hood:
        - '^same step as above except^'
            - found status attribute, in this case, the type of the value of
              the attribute is ovirtsdk.xml.params.Status
            - match() failed because class is compared to string 'up'

     This problem should be attributed to how RHEVM api was designed rather
     than how ovirtsdk handles RHEVM api responses.

    - Obj. are not updated after action calls.
      - E.G.
        vm = api.vms.get(name='test_vm')
        vm.status.get_state() # returns 'down'
        vm.start()
        # wait a few mins
        vm.status.get_state() # returns 'down'; wtf?

        vm = api.vms.get(name='test_vm')
        vm.status.get_state() # returns 'up'
    """

    def __init__(self, hostname, username, password, **kwargs):
        # generate URL from hostname

        if 'port' in kwargs:
            url = 'https://%s:%s/api' % (hostname, kwargs['port'])
        else:
            url = 'https://%s/api' % hostname

        self.api = API(url=url, username=username, password=password, insecure=True)

    def _get_vm(self, vm_name=None):
        if vm_name is None:
            raise Exception('Could not find a VM named %s.' % vm_name)
        else:
            vm = self.api.vms.get(name=vm_name)
            if vm is None:
                raise Exception('Could not find a VM named %s.' % vm_name)
            return vm

    def start_vm(self, vm_name=None):
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            return True
        else:
            ack = vm.start()
            if ack.get_status().get_state() == 'complete':
                return True
        return False

    def stop_vm(self, vm_name):
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            return True
        else:
            ack = vm.stop()
            if ack.get_status().get_state() == 'complete':
                return True
        return False

    def delete_vm(self, vm_name):
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            self.stop_vm(vm_name)
        ack = vm.delete()
        if ack.get_status().get_state() == '':
            return True
        else:
            return False

    def create_vm(self, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')

    def restart_vm(self, vm_name):
        if not self.stop_vm(vm_name):
            return False
        else:
            return self.start_vm(vm_name)

    def list_vm(self, **kwargs):
        # list vm based on kwargs can be buggy
        # i.e. you can't return a list of powered on vm
        # but you can return a vm w/ a matched name
        vm_list = self.api.vms.list(**kwargs)
        return [vm.name for vm in vm_list]

    def list_host(self, **kwargs):
        host_list = self.api.hosts.list(**kwargs)
        return [host.name for host in host_list]

    def list_datastore(self, **kwargs):
        datastore_list = self.api.storagedomains.list(**kwargs)
        return [ds.name for ds in datastore_list if ds.get_status() is None]

    def list_cluster(self, **kwargs):
        cluster_list = self.api.clusters.list(**kwargs)
        return [cluster.name for cluster in cluster_list]

    def list_template(self, **kwargs):
        '''
        CFME ignores the 'Blank' template, so we do too
        '''
        template_list = self.api.templates.list(**kwargs)
        return [template.name for template in template_list if template.name != "Blank"]

    def list_flavor(self):
        raise NotImplementedError('This function is not supported on this platform.')

    def info(self):
        # and we got nothing!
        pass

    def disconnect(self):
        self.api.disconnect()

    def vm_status(self, vm_name=None):
        state = self._get_vm(vm_name).get_status().get_state()
        print "vm " + vm_name + " status is " + state
        return state

    def is_vm_running(self, vm_name):
        state = self.vm_status(vm_name)
        return "up" == state

    def is_vm_stopped(self, vm_name):
        state = self.vm_status(vm_name)
        return "down" == state

    def is_vm_suspended(self, vm_name):
        state = self.vm_status(vm_name)
        return "suspended" == state

    def suspend_vm(self, vm_name):
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            raise Exception('Could not suspend %s because it\'s not running.' % vm_name)
        else:
            ack = vm.suspend()
            return ack.get_status().get_state() == 'complete'

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')


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

    can_suspend = False

    def __init__(self, **kwargs):
        username = kwargs.get('username')
        password = kwargs.get('password')

        region = get_region(kwargs.get('region'))
        self.api = EC2Connection(username, password, region=region)

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

    def list_template(self):
        private_images = self.api.get_all_images(owners=['self'],
                                                 filters={'image-type': 'machine'})
        shared_images = self.api.get_all_images(executable_by=['self'],
                                                filters={'image-type': 'machine'})
        combined_images = list(set(private_images) | set(shared_images))
        return combined_images

    def list_flavor(self):
        raise NotImplementedError('This function is not supported on this platform.')

    def vm_status(self, instance_id):
        """Returns the status of the requested instance

        :param  instance_id: ID of the instance to inspect
        :type   instance_id: basestring
        :return: Instance status.
        :rtype:  basestring

        See this page for possible return values:
        http://docs.aws.amazon.com/AWSEC2/latest/APIReference/
            ApiReference-ItemType-InstanceStateType.html

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
        raise NotImplementedError('This function has not yet been implemented.')

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

    # Prime candidate for a wait_for
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


class OpenstackSystem(MgmtSystemAPIBase):
    """Openstack management system

    Uses novaclient.

    """

    states = {
        'running': ('ACTIVE',),
        'stopped': ('SHUTOFF',),
        'suspended': ('SUSPENDED',),
    }

    can_suspend = True

    def __init__(self, **kwargs):
        tenant = kwargs['tenant']
        username = kwargs['username']
        password = kwargs['password']
        auth_url = kwargs['auth_url']
        self.api = osclient.Client(username, password, tenant, auth_url, service_type="compute")

    def start_vm(self, instance_name):
        if self.is_vm_running(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.start()
        wait_for(self.is_vm_running, [instance_name])
        return True

    def stop_vm(self, instance_name):
        if self.is_vm_stopped(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.stop()
        wait_for(self.is_vm_stopped, [instance_name])
        return True

    def create_vm(self, instance_name, image, flavour, *args, **kwargs):
        """Creates a vm.

        If assign_floating_ip kwarg is present, then create_vm() will
        attempt to register a floating IP address from the pool specified
        in the arg.
        """
        image = self.api.images.find(name=image)
        flavour = self.api.flavors.find(name=flavour)
        instance = self.api.servers.create(instance_name, image, flavour, *args, **kwargs)
        wait_for(self.is_vm_running, [instance_name])

        if 'assign_floating_ip' in kwargs:
            ip = self.api.floating_ips.create(kwargs['assign_floating_ip'])
            instance.add_floating_ip(ip)
        return True

    def delete_vm(self, instance_name):
        instance = self._find_instance_by_name(instance_name)
        return instance.delete()

    def restart_vm(self, instance_name):
        return self.stop_vm(instance_name) and self.start_vm(instance_name)

    def list_vm(self, **kwargs):
        instance_list = self._get_all_instances()
        return [instance.name for instance in instance_list]

    def list_template(self):
        template_list = self.api.images.list()
        return [template.name for template in template_list]

    def list_flavor(self):
        flavor_list = self.api.flavors.list()
        return [flavor.name for flavor in flavor_list]

    def info(self):
        return '%s %s' % (self.api.client.service_type, self.api.client.version)

    def disconnect(self):
        pass

    def vm_status(self, vm_name):
        instance = self._find_instance_by_name(vm_name)
        return instance.status

    def is_vm_running(self, vm_name):
        instance = self._find_instance_by_name(vm_name)
        if instance.status == 'ACTIVE':
            return True
        else:
            return False

    def is_vm_stopped(self, vm_name):
        instance = self._find_instance_by_name(vm_name)
        if instance.status == 'SHUTOFF':
            return True
        else:
            return False

    def is_vm_suspended(self, vm_name):
        instance = self._find_instance_by_name(vm_name)
        if instance.status == 'SUSPENDED':
            return True
        else:
            return False

    def suspend_vm(self, instance_name):
        if self.is_vm_suspended(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.suspend()
        wait_for(self.is_vm_suspended, [instance_name])

    def resume_vm(self, instance_name):
        if self.is_vm_running(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.resume()
        wait_for(self.is_vm_running, [instance_name])

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('clone_vm not implemented.')

    def _get_all_instances(self):
        instances = self.api.servers.list(True, {'all_tenants': True})
        return instances

    def _find_instance_by_name(self, name):
        """
        OpenStack Nova Client does have a find method, but it doesn't
        allow the find method to be used on other tenants. The list()
        method is the only one that allows an all_tenants=True keyword
        """

        instances = self._get_all_instances()
        for instance in instances:
            if instance.name == name:
                return instance
        else:
            raise Exception('Invalid instance ID: %s' % name)


class ActionTimedOutError(Exception):
    pass
