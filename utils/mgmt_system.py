# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""
import re
import time
import boto
from abc import ABCMeta, abstractmethod
from boto.ec2 import EC2Connection, get_region
from functools import partial
from ovirtsdk.api import API
from ovirtsdk.xml import params
from pysphere import VIServer, MORTypes, VITask, VIMor
from pysphere.resources import VimService_services as VI
from pysphere.resources.vi_exception import VIException
from novaclient.v1_1 import client as osclient
from utils.log import logger
from utils.wait import wait_for, TimedOutError


class MgmtSystemAPIBase(object):
    """Base interface class for Management Systems

    Interface notes:

    * Initializers of subclasses must support \*\*kwargs in their
      signtures
    * Action methods (start/stop/etc) should block until the requested
      action is complete

    """
    __metaclass__ = ABCMeta

    # Flag to indicate whether or not this MgmtSystem can suspend,
    # default True
    can_suspend = True

    @abstractmethod
    def start_vm(self, vm_name):
        """Starts a vm.

        Args:
            vm_name: name of the vm to be started
        Returns: whether vm action has been initiated properly
        """
        raise NotImplementedError('start_vm not implemented.')

    @abstractmethod
    def stop_vm(self, vm_name):
        """Stops a vm.

        Args:
            vm_name: name of the vm to be stopped
        Returns: whether vm action has been initiated properly
        """
        raise NotImplementedError('stop_vm not implemented.')

    @abstractmethod
    def create_vm(self, vm_name):
        """Creates a vm.

        Args:
            vm_name: name of the vm to be created
        Returns: whether vm action has been initiated properly
        """
        raise NotImplementedError('create_vm not implemented.')

    @abstractmethod
    def delete_vm(self, vm_name):
        """Deletes a vm.

        Args:
            vm_name: name of the vm to be deleted
        Returns: whether vm action has been initiated properly
        """
        raise NotImplementedError('delete_vm not implemented.')

    @abstractmethod
    def restart_vm(self, vm_name):
        """Restart a vm.

        Args:
            vm_name: name of the vm to be restarted
        Returns: whether vm stop/start have been initiated properly
        """
        raise NotImplementedError('restart_vm not implemented.')

    @abstractmethod
    def list_vm(self, **kwargs):
        """Returns a list of vm names.

        Returns: list of vm names
        """
        raise NotImplementedError('list_vm not implemented.')

    @abstractmethod
    def list_template(self):
        """Returns a list of templates/images.

        Returns: list of template/image names
        """
        raise NotImplementedError('list_template not implemented.')

    @abstractmethod
    def list_flavor(self):
        """Returns a list of flavors.

        Only valid for OpenStack and Amazon

        Returns: list of flavor names
        """
        raise NotImplementedError('list_flavor not implemented.')

    def list_network(self):
        """Returns a list of networks.

        Only valid for OpenStack

        Returns: list of network names
        """
        raise NotImplementedError('list_network not implemented.')

    @abstractmethod
    def info(self):
        """Returns basic information about the mgmt system.

        Returns: string representation of name/version of mgmt system.
        """
        raise NotImplementedError('info not implemented.')

    @abstractmethod
    def disconnect(self):
        """Disconnects the API from mgmt system"""
        raise NotImplementedError('disconnect not implemented.')

    @abstractmethod
    def vm_status(self, vm_name):
        """Status of VM.

        Args:
            vm_name: name of the vm to get status
        Returns: state of the vm
        """
        raise NotImplementedError('vm_status not implemented.')

    @abstractmethod
    def is_vm_running(self, vm_name):
        """Is the vm running?

        Args:
            vm_name: name of the vm
        Returns: whether the vm is running or not
        """
        raise NotImplementedError('is_vm_running not implemented.')

    @abstractmethod
    def is_vm_stopped(self, vm_name):
        """Is the vm stopped?

        Args:
            vm_name: name of the vm
        Returns: whether the vm is stopped or not
        """
        raise NotImplementedError('is_vm_stopped not implemented.')

    @abstractmethod
    def is_vm_suspended(self, vm_name):
        """Is the vm suspended?

        Args:
            vm_name: name of the vm
        Returns: whether the vm is suspended or not
        """
        raise NotImplementedError('is_vm_suspended not implemented.')

    @abstractmethod
    def suspend_vm(self, vm_name):
        """Suspend a vm.

        Args:
            vm_name: name of the vm to be suspended
        Returns: whether vm suspend has been initiated properly
        """
        raise NotImplementedError('restart_vm not implemented.')

    @abstractmethod
    def clone_vm(self, source_name, vm_name):
        """Clone a VM.

        Args:
            source_name: The source VM to clone from
            vm_name: The name of the new VM
        Returns: IP address of the clone
        """
        raise NotImplementedError('clone_vm not implemented.')

    @abstractmethod
    def does_vm_exist(self, name):
        """Does VM exist?

        Args:
            vm_name: The name of the VM
        Returns: whether vm exists
        """
        raise NotImplementedError('does_vm_exist not implemented.')

    @abstractmethod
    def deploy_template(self, template, *args, **kwargs):
        """Deploy a VM from a template

        Args:
            template: The name of the template to deploy
        Returns: name or id(ec2) of vm
        """
        raise NotImplementedError('deploy_template not implemented.')

    @abstractmethod
    def get_ip_address(self, vm_name):
        """get VM ip address

        Args:
            vm_name: The name of the VM
        Returns: vm ip address
        """
        raise NotImplementedError('get_ip_address not implemented.')

    @abstractmethod
    def remove_host_from_cluster(self, hostname):
        """remove a host from it's cluster

        :param hostname: The hostname of the system
        :type  hostname: str
        :return: True if successful, False if failed
        :rtype: boolean

        """

    def stats(self, *requested_stats):
        """Returns all available stats, if none are explicitly requested

        Args:
            *requested_stats: A list giving the name of the stats to return. Stats are defined
                in the _stats_available attibute of the specific class.
        Returns: A dict of stats.
        """
        requested_stats = requested_stats or self._stats_available
        return {stat: self._stats_available[stat](self) for stat in requested_stats}


class VMWareSystem(MgmtSystemAPIBase):
    """Client to Vsphere API

    This class piggy backs off pysphere.

    Benefits of pysphere:
      - Don't need intimate knowledge w/ vsphere api itself.
    Detriments of pysphere:
      - Response often are not detailed enough.

    Args:
        hostname: The hostname of the system.
        username: The username to connect with.
        password: The password to connect with.

    Returns: A :py:class:`VMWareSystem` object.
    """
    _api = None

    _stats_available = {
        'num_vm': lambda self: len(self.list_vm()),
        'num_host': lambda self: len(self.list_host()),
        'num_cluster': lambda self: len(self.list_cluster()),
        'num_template': lambda self: len(self.list_template()),
        'num_datastore': lambda self: len(self.list_datastore()),
    }

    def __init__(self, hostname, username, password, **kwargs):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.api = VIServer()

    @property
    def api(self):
        # wrap calls to the API with a keepalive check, reconnect if needed
        try:
            keepalive = self._api.keep_session_alive()
            if not keepalive:
                logger.debug('The connection to %s "%s" timed out' %
                    (type(self).__name__, self.hostname))
        except VIException as ex:
            if ex.fault == "Not Connected":
                # set this to trigger a connection below
                keepalive = None
            else:
                raise

        if not keepalive:
            self._connect()
        return self._api

    @api.setter
    def api(self, api):
        # Allow for changing the api object via public setter
        self._api = api

    def _connect(self):
        # Since self.api calls _connect, connect via self._api to prevent implosion
        logger.debug('Connecting to %s "%s"' % (type(self).__name__, self.hostname))
        self._api.connect(self.hostname, self.username, self.password)

    def _get_vm(self, vm_name=None):
        """ Returns a vm from the VI object.

        Args:
            vm_name: The name of the VM.

        Returns: a pysphere object.
        """
        if vm_name is None:
            raise VMInstanceNotFound('Could not find a VM named %s.' % vm_name)
        else:
            vm = self.api.get_vm_by_name(vm_name)
            return vm

    def does_vm_exist(self, name):
        """ Checks if a vm exists or not.

        Args:
            name: The name of the requested vm.
        Returns: A boolean, ``True`` if the vm exists, ``False`` if not.
        """
        try:
            self._get_vm(name)
            return True
        except Exception:
            return False

    def _get_resource_pool(self, resource_pool_name=None):
        """ Returns a resource pool MOR for a specified name.

        Args:
            resource_pool_name: The name of the resource pool.
        Returns: The MOR of the resource pool.
        """
        rps = self.api.get_resource_pools()
        for mor, path in rps.iteritems():
            if re.match('.*%s' % resource_pool_name, path):
                return mor
        # Just pick the first
        return rps.keys()[0]

    def get_ip_address(self, vm_name):
        """ Returns the first IP address for the selected VM.

        Args:
            vm_name: The name of the vm to obtain the IP for.
        Returns: A string containing the first found IP that isn't the loopback device.
        """
        vm = self._get_vm(vm_name)
        try:
            net_info, tc = wait_for(vm.get_property, ['net', False],
                                    fail_condition=None, delay=5, num_sec=600,
                                    message="get_ip_address from vsphere")
        except TimedOutError:
            net_info = None

        if net_info:
            ipv4_re = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
            for ip in net_info[0]['ip_addresses']:
                if re.match(ipv4_re, ip) and ip != '127.0.0.1':
                    return ip
        return None

    def _get_list_vms(self, get_template=False):
        """ Obtains a list of all VMs on the system.

        Optional flag to obtain template names too.

        Args:
            get_template: A boolean describing if it should return template names also.
        Returns: A list of VMs.
        """
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
        logger.info(" Starting vSphere VM %s" % vm_name)
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
        logger.info(" Stopping vSphere VM %s" % vm_name)
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
        logger.info(" Deleting vSphere VM %s" % vm_name)
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
        logger.info(" Restarting vSphere VM %s" % vm_name)
        return self.stop_vm(vm_name) and self.start_vm(vm_name)

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
        return self.vm_status(vm_name) == "POWERED ON"

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) == "POWERED OFF"

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == "SUSPENDED"

    def suspend_vm(self, vm_name):
        logger.info(" Suspending vSphere VM %s" % vm_name)
        vm = self._get_vm(vm_name)
        if vm.is_powered_off():
            raise VMInstanceNotSuspended(vm_name)
        else:
            vm.suspend()
            return self.is_vm_suspended(vm_name)

    def clone_vm(self):
        raise NotImplementedError('clone_vm not implemented.')

    def deploy_template(self, template, *args, **kwargs):
        logger.info(" Deploying vSphere template %s to VM %s" % (template, kwargs["vm_name"]))
        if 'resourcepool' not in kwargs:
            kwargs['resourcepool'] = None
        vm = self._get_vm(template)
        if vm:
            vm.clone(kwargs['vm_name'], sync_run=True,
                resourcepool=self._get_resource_pool(kwargs['resourcepool']))
            return kwargs['vm_name']
        else:
            raise VMInstanceNotCloned(template)

    def remove_host_from_cluster(self, hostname):
        req = VI.DisconnectHost_TaskRequestMsg()
        mor = (key for key, value in self.api.get_hosts().items() if value == hostname).next()
        sys = VIMor(mor, 'HostSystem')
        _this = req.new__this(sys)
        _this.set_attribute_type(sys.get_attribute_type())
        req.set_element__this(_this)
        task_mor = self.api._proxy.DisconnectHost_Task(req)._returnval
        t = VITask(task_mor, self.api)
        wait_for(lambda: 'success' in t.get_state())
        self._destroy_host(hostname)

    def _destroy_host(self, hostname):
        req = VI.Destroy_TaskRequestMsg()
        mor = (key for key, value in self.api.get_hosts().items() if value == hostname).next()
        sys = VIMor(mor, 'HostSystem')
        _this = req.new__this(sys)
        _this.set_attribute_type(sys.get_attribute_type())
        req.set_element__this(_this)
        task_mor = self.api._proxy.Destroy_Task(req)._returnval
        t = VITask(task_mor, self.api)
        wait_for(lambda: 'success' in t.get_state())


class RHEVMSystem(MgmtSystemAPIBase):
    """
    Client to RHEVM API

    This class piggy backs off ovirtsdk.

    Benefits of ovirtsdk:

    * Don't need intimite knowledge w/ RHEVM api itself.

    Detriments of ovirtsdk:

    * Response to most quaries are returned as an object rather than a string.
      This makes it harder to do simple stuff like getting the status of a vm.
    * Because of this, it makes listing VMs based on \*\*kwargs impossible
      since ovirtsdk relies on re class to find matches.

      * | For example: List out VM with this name (positive case)
        | Ideal: self.api.vms.list(name='test_vm')
        | Underneath the hood:

        * ovirtsdk fetches list of all vms [ovirtsdk.infrastructure.brokers.VM
          object, ...]
        * ovirtsdk then tries to filter the result using re.

          * tries to look for 'name' attr in ovirtsdk.infrastructure.brokers.VM
            object
          * found name attribute, in this case, the type of the value of the
            attribute is string.
          * match() succeed in comparing the value to 'test_vm'

      * | For example: List out VM with that's powered on (negative case)
        | Ideal: self.api.vms.list(status='up')
        | Underneath the hood:

        * **same step as above except**

          * found status attribute, in this case, the type of the value of
            the attribute is ovirtsdk.xml.params.Status
          * match() failed because class is compared to string 'up'

     This problem should be attributed to how RHEVM api was designed rather
     than how ovirtsdk handles RHEVM api responses.

    * Obj. are not updated after action calls.

      * For example::
          vm = api.vms.get(name='test_vm')
          vm.status.get_state() # returns 'down'
          vm.start()
          # wait a few mins
          vm.status.get_state() # returns 'down'; wtf?

          vm = api.vms.get(name='test_vm')
          vm.status.get_state() # returns 'up'

    Args:
        hostname: The hostname of the system.
        username: The username to connect with.
        password: The password to connect with.

    Returns: A :py:class:`RHEVMSystem` object.
    """

    _stats_available = {
        'num_vm': lambda self: self.api.get_summary().get_vms().total,
        'num_host': lambda self: len(self.list_host()),
        'num_cluster': lambda self: len(self.list_cluster()),
        'num_template': lambda self: len(self.list_template()),
        'num_datastore': lambda self: len(self.list_datastore()),
    }

    def __init__(self, hostname, username, password, **kwargs):
        # generate URL from hostname

        if 'port' in kwargs:
            url = 'https://%s:%s/api' % (hostname, kwargs['port'])
        else:
            url = 'https://%s/api' % hostname

        self._api = None
        self._api_kwargs = {
            'url': url,
            'username': username,
            'password': password,
            'insecure': True
        }

    @property
    def api(self):
        if self._api is None:
            self._api = API(**self._api_kwargs)
        return self._api

    def _get_vm(self, vm_name=None):
        """ Returns a vm from the RHEVM object.

        Args:
            vm_name: The name of the VM.

        Returns: an ovirtsdk vm object.
        """
        if vm_name is None:
            raise VMInstanceNotFound(vm_name)
        else:
            vm = self.api.vms.get(name=vm_name)
            if vm is None:
                raise VMInstanceNotFound(vm_name)
            return vm

    def get_ip_address(self, vm_name):
        vm = self._get_vm(vm_name)
        return vm.get_guest_info().get_ips().get_ip()[0].get_address()

    def does_vm_exist(self, name):
        try:
            self._get_vm(name)
            return True
        except VMInstanceNotFound:
            return False

    def start_vm(self, vm_name=None):
        logger.debug(' Starting RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            return True
        else:
            vm.start()
            wait_for(
                lambda: self.is_vm_running(vm_name),
                num_sec=180,
                delay=5,
                message="RHEV VM %s started" % vm_name
            )
            return True

    def stop_vm(self, vm_name):
        logger.debug(' Stopping RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            return True
        else:
            vm.stop()
            wait_for(
                lambda: self.is_vm_stopped(vm_name),
                num_sec=180,
                delay=5,
                message="RHEV VM %s stopped" % vm_name
            )
            return True

    def delete_vm(self, vm_name):
        logger.debug(' Deleting RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        self.stop_vm(vm_name)
        vm.delete()
        wait_for(
            lambda: self.does_vm_exist(vm_name),
            fail_condition=True,
            message="wait for RHEV VM %s deleted" % vm_name
        )
        return True

    def create_vm(self, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')
    # Heres the code but don't have a need and no time to test it to get it right
    #   including for inclusion later
    #
    # def create_vm(self, vm_name, *args, **kwargs):
    #     MB = 1024 * 1024
    #     try:
    #         self.api.vms.add(
    #             params.VM(
    #                 name=vm_name,
    #                 memory=kwargs['memory_in_mb'] * MB,
    #                 cluster=self.api.clusters.get(kwargs['cluster_name']),
    #                 template=self.api.templates.get('Blank')))
    #         print 'VM created'
    #         self.api.vms.get(vm_name).nics.add(params.NIC(name='eth0',
    #             network=params.Network(name='ovirtmgmt'), interface='virtio'))
    #         print 'NIC added to VM'
    #         self.api.vms.get(vm_name).disks.add(params.Disk(
    #             storage_domains=params.StorageDomains(
    #                 storage_domain=[self.api.storagedomains.get(kwargs['storage_domain'])],
    #                 size=512 * MB,
    #                 status=None,
    #                 interface='virtio',
    #                 format='cow',
    #                 sparse=True,
    #                 bootable=True)))
    #         print 'Disk added to VM'
    #         print 'Waiting for VM to reach Down status'
    #         while self.api.vms.get(vm_name).status.state != 'down':
    #             time.sleep(1)
    #     except Exception as e:
    #         print 'Failed to create VM with disk and NIC\n%s' % str(e)

    def restart_vm(self, vm_name):
        logger.debug(' Restarting RHEV VM %s' % vm_name)
        return self.stop_vm(vm_name) and self.start_vm(vm_name)

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
        """
        Note: CFME ignores the 'Blank' template, so we do too
        """
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
        return self._get_vm(vm_name).get_status().get_state()

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) == "up"

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) == "down"

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == "suspended"

    def suspend_vm(self, vm_name):
        logger.debug(' Suspending RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            raise VMInstanceNotSuspended(vm_name)
        elif vm.status.get_state() == 'suspended':
            return True
        else:
            vm.suspend()
            wait_for(
                lambda: self.is_vm_suspended(vm_name),
                message="wait for RHEV VM %s suspended" % vm_name
            )
            return True

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')

    def deploy_template(self, template, *args, **kwargs):
        logger.debug(' Deploying RHEV template %s to VM %s' % (template, kwargs["vm_name"]))
        self.api.vms.add(params.VM(
            name=kwargs['vm_name'],
            cluster=self.api.clusters.get(kwargs['cluster_name']),
            template=self.api.templates.get(template)))
        wait_for(
            lambda: self.is_vm_stopped(kwargs['vm_name']),
            num_sec=300,
            delay=5,
            message="wait for RHEV VM %s powered off after provisioning" % kwargs['vm_name']
        )
        self.start_vm(kwargs['vm_name'])
        return kwargs['vm_name']

    def remove_host_from_cluster(self, hostname):
        raise NotImplementedError('remove_host_from_cluster not implemented')


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

    Args:
        *kwargs: Arguments to connect, usually, username, password, region.
    Returns: A :py:class:`EC2System` object.
    """

    _stats_available = {
        'num_vm': lambda self: len(self.list_vm()),
        'num_template': lambda self: len(self.list_template()),
    }

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

        Args:
            instance_id: ID of the instance to inspect
        Returns: Instance status.

        See this `page <http://docs.aws.amazon.com/AWSEC2/latest/APIReference/
        ApiReference-ItemType-InstanceStateType.html>`_ for possible return values.

        """
        instance_id = self._get_instance_id_by_name(instance_id)
        reservations = self.api.get_all_instances([instance_id])
        instances = self._get_instances_from_reservations(reservations)
        for instance in instances:
            if instance.id == instance_id:
                return instance.state

    def create_vm(self):
        raise NotImplementedError('create_vm not implemented.')

    def delete_vm(self, instance_id):
        """Deletes the an instance

        Args:
            instance_id: ID of the instance to act on
        Returns: Whether or not the backend reports the action completed
        """
        logger.info(" Terminating EC2 instance %s" % instance_id)
        instance_id = self._get_instance_id_by_name(instance_id)
        try:
            self.api.terminate_instances([instance_id])
            self._block_until(instance_id, self.states['deleted'])
            return True
        except ActionTimedOutError:
            return False

    def start_vm(self, instance_id):
        """Start an instance

        Args:
            instance_id: ID of the instance to act on
        Returns: Whether or not the backend reports the action completed
        """
        logger.info(" Starting EC2 instance %s" % instance_id)
        instance_id = self._get_instance_id_by_name(instance_id)
        try:
            self.api.start_instances([instance_id])
            self._block_until(instance_id, self.states['running'])
            return True
        except ActionTimedOutError:
            return False

    def stop_vm(self, instance_id):
        """Stop an instance

        Args:
            instance_id: ID of the instance to act on
        Returns: Whether or not the backend reports the action completed
        """
        logger.info(" Stopping EC2 instance %s" % instance_id)
        instance_id = self._get_instance_id_by_name(instance_id)
        try:
            self.api.stop_instances([instance_id])
            self._block_until(instance_id, self.states['stopped'])
            return True
        except ActionTimedOutError:
            return False

    def restart_vm(self, instance_id):
        """Restart an instance

        Args:
            instance_id: ID of the instance to act on
        Returns: Whether or not the backend reports the action completed

        The action is taken in two separate calls to EC2. A 'False' return can
        indicate a failure of either the stop action or the start action.

        Note: There is a reboot_instances call available on the API, but it provides
            less insight than blocking on stop_vm and start_vm. Furthermore,
            there is no "rebooting" state, so there are potential monitoring
            issues that are avoided by completing these steps atomically
        """
        logger.info(" Restarting EC2 instance %s" % instance_id)
        return self.stop_vm(instance_id) and self.start_vm(instance_id)

    def is_vm_running(self, instance_id):
        """Is the VM running?

        Args:
            instance_id: ID of the instance to inspect
        Returns: Whether or not the requested instance is running
        """
        return self.vm_status(instance_id) in self.states['running']

    def is_vm_stopped(self, instance_id):
        """Is the VM stopped?

        Args:
            instance_id: ID of the instance to inspect
        Returns: Whether or not the requested instance is stopped
        """
        return self.vm_status(instance_id) in self.states['stopped']

    def suspend_vm(self, instance_id):
        """Suspend a VM: Unsupported by EC2

        Args:
            instance_id: ID of the instance to act on
        Raises:
            ActionNotSupported: The action is not supported on the system
        """
        raise ActionNotSupported()

    def is_vm_suspended(self, instance_id):
        """Is the VM suspended? We'll never know because EC2 don't support this.

        Args:
            instance_id: ID of the instance to inspect
        Raises:
            ActionNotSupported: The action is not supported on the system
        """
        raise ActionNotSupported()

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')

    def deploy_template(self, template, *args, **kwargs):
        """Instantiate the requested template image

        Args:
            ami_id: AMI ID to instantiate
        Returns: Instance ID of the created instance

        Packed arguments are passed along to boto's run_instances method.

        Note: min_count and max_count will be forced to '1'; if you're trying to do
            anything fancier than that, you might be in the wrong place

        """
        # Enforce create_vm only creating one VM
        logger.info(" Deploying EC2 template %s" % template)
        kwargs.update({
            'min_count': 1,
            'max_count': 1,
        })
        reservation = self.api.run_instances(template, *args, **kwargs)
        instances = self._get_instances_from_reservations([reservation])
        # Should have only made one VM; return its ID for use in other methods
        while not self.is_vm_running(instances[0].id):
            time.sleep(5)
        return instances[0].id

    def _get_instance_by_id(self, instance_id):
        inst_list = self._get_all_instances()
        for instance in inst_list:
            if instance.id == instance_id:
                return instance

    def get_ip_address(self, id):
        return str(self._get_instance_by_id(id).ip_address)

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
            raise VMInstanceNotFound(instance_name)
        elif len(instances) > 1:
            raise MultipleInstancesError('Instance name "%s" is not unique' % instance_name)
        else:
            # We have an instance! return its ID
            return instances[0].id

    def does_vm_exist(self, name):
        try:
            self._get_instance_id_by_name(name)
            return True
        except MultipleInstancesError:
            return True
        except Exception:
            return True

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

    def remove_host_from_cluster(self, hostname):
        raise NotImplementedError('remove_host_from_cluster not implemented')


class OpenstackSystem(MgmtSystemAPIBase):
    """Openstack management system

    Uses novaclient.

    Args:
        tenant: The tenant to log in with.
        username: The username to connect with.
        password: The password to connect with.
        auth_url: The authentication url.

    """

    _stats_available = {
        'num_vm': lambda self: len(self.list_vm()),
        'num_template': lambda self: len(self.list_template()),
    }

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
        logger.info(" Starting OpenStack instance %s" % instance_name)
        if self.is_vm_running(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.start()
        wait_for(lambda: self.is_vm_running(instance_name), message="start %s" % instance_name)
        return True

    def stop_vm(self, instance_name):
        logger.info(" Stopping OpenStack instance %s" % instance_name)
        if self.is_vm_stopped(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.stop()
        wait_for(lambda: self.is_vm_stopped(instance_name), message="stop %s" % instance_name)
        return True

    def create_vm(self):
        raise NotImplementedError('create_vm not implemented.')

    def delete_vm(self, instance_name):
        logger.info(" Deleting OpenStack instance %s" % instance_name)
        instance = self._find_instance_by_name(instance_name)
        instance.delete()
        return self.does_vm_exist(instance_name)

    def restart_vm(self, instance_name):
        logger.info(" Restarting OpenStack instance %s" % instance_name)
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

    def list_network(self):
        network_list = self.api.networks.list()
        return [network.label for network in network_list]

    def info(self):
        return '%s %s' % (self.api.client.service_type, self.api.client.version)

    def disconnect(self):
        pass

    def vm_status(self, vm_name):
        return self._find_instance_by_name(vm_name).status

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) == 'ACTIVE'

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) == 'SHUTOFF'

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == 'SUSPENDED'

    def suspend_vm(self, instance_name):
        logger.info(" Suspending OpenStack instance %s" % instance_name)
        if self.is_vm_suspended(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.suspend()
        wait_for(lambda: self.is_vm_suspended(instance_name), message="suspend %s" % instance_name)

    def resume_vm(self, instance_name):
        logger.info(" Resuming OpenStack instance %s" % instance_name)
        if self.is_vm_running(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.resume()
        wait_for(lambda: self.is_vm_running(instance_name), message="%s resumed" % instance_name)

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('clone_vm not implemented.')

    def deploy_template(self, template, *args, **kwargs):
        """ Deploys a vm from a template.

        Args:
            template: The name of the template to use.
            flavour_name: The name of the flavour to use.
            vm_name: A name to use for the vm.
            network_name: The name of the network if it is a multi network setup (Havanna).

        Note: If assign_floating_ip kwarg is present, then :py:meth:`OpenstackSystem.create_vm` will
            attempt to register a floating IP address from the pool specified in the arg.
        """
        nics = []
        # defaults
        if 'flavour_name' not in kwargs:
            kwargs['flavour_name'] = 'm1.tiny'
        if 'vm_name' not in kwargs:
            kwargs['vm_name'] = 'new_instance_name'
        logger.info(" Deploying OpenStack template %s to instance %s (%s)" % (
            template, kwargs["vm_name"], kwargs["flavour_name"]))
        if len(self.list_network()) > 1:
            if 'network_name' not in kwargs:
                raise NetworkNameNotFound('Must select a network name')
            else:
                net_id = self.api.networks.find(label=kwargs['network_name']).id
                nics = [{'net-id': net_id}]

        image = self.api.images.find(name=template)
        flavour = self.api.flavors.find(name=kwargs['flavour_name'])
        instance = self.api.servers.create(kwargs['vm_name'], image, flavour, nics=nics,
                                           *args, **kwargs)
        wait_for(lambda: self.is_vm_running(kwargs["vm_name"]),
            message="OS instance %s running after provision" % kwargs['vm_name'])

        if kwargs.get('assign_floating_ip', None) is not None:
            ip = self.api.floating_ips.create(kwargs['assign_floating_ip'])
            instance.add_floating_ip(ip)

        return kwargs['vm_name']

    def _get_instance_networks(self, name):
        instance = self._find_instance_by_name(name)
        return instance._info['addresses']

    def get_ip_address(self, name):
        networks = self._get_instance_networks(name)
        for network_nics in networks.itervalues():
            for nic in network_nics:
                if nic['OS-EXT-IPS:type'] == 'floating':
                    return str(nic['addr'])

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
            raise VMInstanceNotFound(name)

    def does_vm_exist(self, name):
        try:
            self._find_instance_by_name(name)
            return True
        except Exception:
            return False

    def remove_host_from_cluster(self, hostname):
        raise NotImplementedError('remove_host_from_cluster not implemented')


class ActionNotSupported(Exception):
    """Raised when an action is not supported."""
    pass


class ActionTimedOutError(Exception):
    pass


class MultipleInstancesError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class NetworkNameNotFound(Exception):
    pass


class VMInstanceNotCloned(Exception):
    """Raised if a VM is not found."""
    def __init__(self, template):
        self.template = template

    def __str__(self):
        return 'Could not clone %s' % self.template


class VMInstanceNotFound(Exception):
    """Raised if a VM is not found."""
    def __init__(self, vm_name):
        self.vm_name = vm_name

    def __str__(self):
        return 'Could not find a VM named %s.' % self.vm_name


class VMInstanceNotSuspended(Exception):
    """Raised if a VM is not able to be suspended."""
    def __init__(self, vm_name):
        self.vm_name = vm_name

    def __str__(self):
        return 'Could not suspend %s because it\'s not running.' % self.vm_name
