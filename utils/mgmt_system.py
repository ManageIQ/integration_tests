# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""
import re
import winrm
from abc import ABCMeta, abstractmethod
from cStringIO import StringIO
from datetime import datetime
from textwrap import dedent
import operator

import boto
import tzlocal
from boto.ec2 import EC2Connection, get_region
from keystoneclient.v2_0 import client as oskclient
from lxml import etree
from novaclient.v1_1 import client as osclient
from ovirtsdk.api import API
from ovirtsdk.infrastructure.errors import DisconnectedError
from ovirtsdk.xml import params
from psphere import managedobjects as mobs
from psphere.client import Client
from psphere.errors import ObjectNotFoundError

from cfme import exceptions as cfme_exc
from utils.log import logger
from utils.version import LooseVersion, current_version
from utils.wait import wait_for, TimedOutError

local_tz = tzlocal.get_localzone()


class _PsphereClient(Client):
    def get_search_filter_spec(self, *args, **kwargs):
        # A datastore traversal spec is missing from this method in psphere.
        # psav has opened a PR to add it, but until it gets merged we'll need to come behind
        # psphere and add it in just like his PR does
        # https://github.com/jkinred/psphere/pull/18/files
        pfs = super(_PsphereClient, self).get_search_filter_spec(*args, **kwargs)
        select_sets = pfs.objectSet[0].selectSet
        missing_ss = 'datacenter_datastore_traversal_spec'
        ss_names = [ss.name for ss in select_sets]

        if missing_ss not in ss_names:
            logger.trace('Injecting %s into psphere search filter spec', missing_ss)
            # pull out the folder traversal spec traversal specs
            fts_ts = pfs.objectSet[0].selectSet[0]
            # and get the select set from the traversal spec
            fts_ss = fts_ts.selectSet[0]

            # add ds selection spec to folder traversal spec
            dsss = self.create('SelectionSpec', name=missing_ss)
            fts_ts.selectSet.append(dsss)

            # add ds traversal spec to search filter object set select spec
            dsts = self.create('TraversalSpec')
            dsts.name = 'datacenter_datastore_traversal_spec'
            dsts.type = 'Datacenter'
            dsts.path = 'datastoreFolder'
            dsts.selectSet = [fts_ss]
            select_sets.append(dsts)
        else:
            logger.warning('%s already in psphere search filer spec, not adding it', missing_ss)

        return pfs


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
    def wait_vm_running(self, vm_name, num_sec):
        """Waits for a VM to be running.

        Args:
            vm_name: name of the vm to be running
            num_sec: number of seconds before timeout
        """
        raise NotImplementedError('wait_vm_running not implemented.')

    @abstractmethod
    def stop_vm(self, vm_name):
        """Stops a vm.

        Args:
            vm_name: name of the vm to be stopped
        Returns: whether vm action has been initiated properly
        """
        raise NotImplementedError('stop_vm not implemented.')

    @abstractmethod
    def wait_vm_stopped(self, vm_name, num_sec):
        """Waits for a VM to be stopped.

        Args:
            vm_name: name of the vm to be stopped
            num_sec: number of seconds before timeout
        """
        raise NotImplementedError('wait_vm_stopped not implemented.')

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
    def wait_vm_suspended(self, vm_name, num_sec):
        """Waits for a VM to be suspended.

        Args:
            vm_name: name of the vm to be suspended
            num_sec: number of seconds before timeout
        """
        raise NotImplementedError('wait_vm_suspended not implemented.')

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
    def current_ip_address(self, vm_name):
        """Returns current IP address. Returns None if the address could not have been determined.

        Args:
            vm_name: The name of the VM
        Returns: vm ip address or None
        """
        raise NotImplementedError('current_ip_address not implemented.')

    @abstractmethod
    def get_ip_address(self, vm_name):
        """get VM ip address - blocks until the waiting is finished

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

    def in_steady_state(self, vm_name):
        """Return whether the specified virtual machine is in steady state

        Args:
            vm_name: VM name
        Returns: boolean
        """
        return (
            self.is_vm_running(vm_name)
            or self.is_vm_stopped(vm_name)
            or self.is_vm_suspended(vm_name)
        )

    def wait_vm_steady(self, vm_name, num_sec=120):
        """Waits 2 (or user-specified time) minutes for VM to settle in steady state

        Args:
            vm_name: VM name
            num_sec: Timeout for wait_for
        """
        return wait_for(
            lambda: self.in_steady_state(vm_name),
            num_sec=num_sec,
            delay=2,
            message="VM %s in steady state" % vm_name
        )


class VMWareSystem(MgmtSystemAPIBase):
    """Client to Vsphere API

    Args:
        hostname: The hostname of the system.
        username: The username to connect with.
        password: The password to connect with.

    See also:

        vSphere Management SDK API docs
        https://developercenter.vmware.com/web/dp/doc/preview?id=155

    """
    _api = None

    _stats_available = {
        'num_vm': lambda self: len(self.list_vm()),
        'num_host': lambda self: len(self.list_host()),
        'num_cluster': lambda self: len(self.list_cluster()),
        'num_template': lambda self: len(self.list_template()),
        'num_datastore': lambda self: len(self.list_datastore()),
    }
    POWERED_ON = 'poweredOn'
    POWERED_OFF = 'poweredOff'
    SUSPENDED = 'suspended'

    def __init__(self, hostname, username, password, **kwargs):
        self.hostname = hostname
        self.username = username
        self.password = password
        self._api = None
        self._vm_cache = {}
        self.kwargs = kwargs

    @property
    def api(self):
        if not self._api:
            self._api = _PsphereClient(self.hostname, self.username, self.password)
        return self._api

    @property
    def version(self):
        return LooseVersion(self.api.si.content.about.version)

    @property
    def default_resource_pool(self):
        return self.kwargs.get("default_resource_pool", None)

    def _get_vm(self, vm_name, force=False):
        """ Returns a vm from the VI object.

        Args:
            vm_name: The name of the VM.
            force: Ignore the cache when updating

        Returns: a psphere object.
        """
        if vm_name not in self._vm_cache or force:
            self._vm_cache[vm_name] = mobs.VirtualMachine.get(self.api, name=vm_name)
        else:
            self._vm_cache[vm_name].update()

        return self._vm_cache[vm_name]

    def _get_resource_pool(self, resource_pool_name=None):
        """ Returns a resource pool MOR for a specified name.

        Args:
            resource_pool_name: The name of the resource pool. If None, first one will be picked.
        Returns: The MOR of the resource pool.
        """
        if resource_pool_name is not None:
            return mobs.ResourcePool.get(self.api, name=resource_pool_name)
        elif self.default_resource_pool is not None:
            return mobs.ResourcePool.get(self.api, name=self.default_resource_pool)
        else:
            return mobs.ResourcePool.all(self.api)[0]

    @staticmethod
    def _task_wait(task):
        task.update()
        if task.info.state not in ['queued', 'running', None]:
            return task.info.state

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

    def current_ip_address(self, vm_name):
        ipv4_re = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        try:
            vm = self._get_vm(vm_name)
            ip_address = vm.summary.guest.ipAddress
            if not re.match(ipv4_re, ip_address) or ip_address == '127.0.0.1':
                ip_address = None
            return ip_address
        except (AttributeError, TypeError):
            # AttributeError: vm doesn't have an ip address yet
            # TypeError: ip address wasn't a string
            return None

    def get_ip_address(self, vm_name, timeout=600):
        """ Returns the first IP address for the selected VM.

        Args:
            vm_name: The name of the vm to obtain the IP for.
            timeout: The IP address wait timeout.
        Returns: A string containing the first found IP that isn't the loopback device.
        """
        try:
            ip_address, tc = wait_for(lambda: self.current_ip_address(vm_name),
                fail_condition=None, delay=5, num_sec=timeout,
                message="get_ip_address from vsphere")
        except TimedOutError:
            ip_address = None
        return ip_address

    def _get_list_vms(self, get_template=False):
        """ Obtains a list of all VMs on the system.

        Optional flag to obtain template names too.

        Args:
            get_template: A boolean describing if it should return template names also.
        Returns: A list of VMs.
        """
        # Use some psphere internals to get vm propsets back directly with requested properties,
        # so we skip the network overhead of returning full managed objects
        property_spec = self.api.create('PropertySpec')
        property_spec.all = False
        property_spec.pathSet = ['name', 'config.template']
        property_spec.type = 'VirtualMachine'
        pfs = self.api.get_search_filter_spec(self.api.si.content.rootFolder, property_spec)
        object_contents = self.api.si.content.propertyCollector.RetrieveProperties(specSet=[pfs])

        # Ensure get_template is either True or False to match the config.template property
        get_template = bool(get_template)

        # Select the vms or templates based on get_template and the returned properties
        obj_list = []
        for object_content in object_contents:
            # Nested property lookups work, but the attr lookup on the
            # vm object still triggers a request even though the vm
            # object already "knows" the answer in its cached object
            # content. So we just pull the value straight out of the cache.
            vm_props = {p.name: p.val for p in object_content.propSet}

            if vm_props.get('config.template') == get_template:
                obj_list.append(vm_props['name'])
        return obj_list

    def get_vm_name_from_ip(self, ip):
        """ Gets the name of a vm from its IP.

        Args:
            ip: The ip address of the vm.
        Returns: The vm name for the corresponding IP."""
        vms = self.api.si.content.searchIndex.FindAllByIp(ip=ip, vmSearch=True)
        # As vsphere remembers the last IP a vm had, when we search we get all
        # of them. Consequently we need to store them all in a dict and then sort
        # them to find out which one has the latest boot time. I am going out on
        # a limb and saying that searching for several vms and querying each object
        # is quicker than finding all machines and recording the bootTime and ip address
        # of each, before iterating through all of them to weed out the ones we care
        # about, but I could be wrong.
        boot_times = {}
        for vm in vms:
            if vm.name not in boot_times:
                boot_times[vm.name] = datetime.fromtimestamp(0)
                try:
                    boot_times[vm.name] = vm.summary.runtime.bootTime
                except:
                    pass
        if boot_times:
            newest_boot_time = sorted(boot_times.items(), key=operator.itemgetter(1),
                                      reverse=True)[0]
            return newest_boot_time[0]
        else:
            raise cfme_exc.VmNotFoundViaIP('The requested IP is not known as a VM')

    def start_vm(self, vm_name):
        self.wait_vm_steady(vm_name)
        if self.is_vm_running(vm_name):
            logger.info(" vSphere VM %s is already running" % vm_name)
            return True
        else:
            logger.info(" Starting vSphere VM %s" % vm_name)
            vm = self._get_vm(vm_name)
            vm.PowerOnVM_Task()
            self.wait_vm_running(vm_name)
            return True

    def stop_vm(self, vm_name):
        self.wait_vm_steady(vm_name)
        if self.is_vm_stopped(vm_name):
            logger.info(" vSphere VM %s is already stopped" % vm_name)
            return True
        else:
            logger.info(" Stopping vSphere VM %s" % vm_name)
            vm = self._get_vm(vm_name)
            if self.is_vm_suspended(vm_name):
                logger.info(
                    " Resuming suspended VM %s before stopping." % vm_name
                )
                vm.PowerOnVM_Task()
                self.wait_vm_running(vm_name)
            vm.PowerOffVM_Task()
            self.wait_vm_stopped(vm_name)
            return True

    def delete_vm(self, vm_name):
        self.wait_vm_steady(vm_name)
        logger.info(" Deleting vSphere VM %s" % vm_name)
        vm = self._get_vm(vm_name)
        self.stop_vm(vm_name)

        task = vm.Destroy_Task()
        status, t = wait_for(self._task_wait, [task])
        return status == 'success'

    def is_host_connected(self, host_name):
        host = mobs.HostSystem.get(self.api, name=host_name)
        return True if host.summary.runtime.connectionState == "connected" else False

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
        return [str(h.name) for h in mobs.HostSystem.all(self.api)]

    def list_datastore(self):
        return [str(h.name) for h in mobs.Datastore.all(self.api) if h.host]

    def list_cluster(self):
        return [str(h.name) for h in mobs.ClusterComputeResource.all(self.api)]

    def list_resource_pools(self):
        return [str(h.name) for h in mobs.ResourcePool.all(self.api)]

    def info(self):
        return '%s %s' % (self.api.get_server_type(), self.api.get_api_version())

    def connect(self):
        pass

    def disconnect(self):
        pass

    def vm_status(self, vm_name):
        return self._get_vm(vm_name, force=True).runtime.powerState

    def vm_creation_time(self, vm_name):
        # psphere turns date strings in datetime for us
        vm = self._get_vm(vm_name)
        return vm.runtime.bootTime

    def in_steady_state(self, vm_name):
        return self.vm_status(vm_name) in {self.POWERED_ON, self.POWERED_OFF, self.SUSPENDED}

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) == self.POWERED_ON

    def wait_vm_running(self, vm_name, num_sec=240):
        logger.info(" Waiting for vSphere VM %s to change status to ON" % vm_name)
        wait_for(self.is_vm_running, [vm_name], num_sec=num_sec)

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) == self.POWERED_OFF

    def wait_vm_stopped(self, vm_name, num_sec=240):
        logger.info(" Waiting for vSphere VM %s to change status to OFF" % vm_name)
        wait_for(self.is_vm_stopped, [vm_name], num_sec=num_sec)

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == self.SUSPENDED

    def wait_vm_suspended(self, vm_name, num_sec=360):
        logger.info(" Waiting for vSphere VM %s to change status to SUSPENDED" % vm_name)
        wait_for(self.is_vm_suspended, [vm_name], num_sec=num_sec)

    def suspend_vm(self, vm_name):
        self.wait_vm_steady(vm_name)
        logger.info(" Suspending vSphere VM %s" % vm_name)
        vm = self._get_vm(vm_name)
        if self.is_vm_stopped(vm_name):
            raise VMInstanceNotSuspended(vm_name)
        else:
            vm.SuspendVM_Task()
            self.wait_vm_suspended(vm_name)
            return True

    def clone_vm(self, source, destination, resourcepool=None, datastore=None, power_on=True,
                 sparse=False, template=False, provision_timeout=900):
        try:
            if mobs.VirtualMachine.get(self.api, name=destination).name == destination:
                raise Exception("VM already present!")
        except ObjectNotFoundError:
            pass

        source_template = mobs.VirtualMachine.get(self.api, name=source)

        vm_clone_spec = self.api.create("VirtualMachineCloneSpec")
        vm_reloc_spec = self.api.create("VirtualMachineRelocateSpec")
        # DATASTORE
        if isinstance(datastore, basestring):
            vm_reloc_spec.datastore = mobs.Datastore.get(self.api, name=datastore)
        elif isinstance(datastore, mobs.Datastore):
            vm_reloc_spec.datastore = datastore
        elif datastore is None:
            datastores = source_template.datastore
            if isinstance(datastores, (list, tuple)):
                vm_reloc_spec.datastore = datastores[0]
            else:
                vm_reloc_spec.datastore = datastores
        else:
            raise NotImplementedError("{} not supported for datastore".format(datastore))

        # RESOURCE POOL
        if isinstance(resourcepool, mobs.ResourcePool):
            vm_reloc_spec.pool = resourcepool
        else:
            vm_reloc_spec.pool = self._get_resource_pool(resourcepool)

        vm_reloc_spec.host = None
        if sparse:
            vm_reloc_spec.transform = self.api.create('VirtualMachineRelocateTransformation').sparse
        else:
            vm_reloc_spec.transform = self.api.create('VirtualMachineRelocateTransformation').flat

        vm_clone_spec.powerOn = power_on
        vm_clone_spec.template = template
        vm_clone_spec.location = vm_reloc_spec
        vm_clone_spec.snapshot = None

        try:
            folder = source_template.parent.parent.vmParent
        except AttributeError:
            folder = source_template.parent

        task = source_template.CloneVM_Task(folder=folder, name=destination, spec=vm_clone_spec)
        wait_for(
            lambda: task.info.state not in {"queued", "running"},
            fail_func=task.update, num_sec=provision_timeout, delay=4
        )
        if task.info.state != 'success':
            logger.error('Clone VM failed: {}'.format(task.info.error.localizedMessage))
            raise VMInstanceNotCloned(source)
        else:
            return destination

    def mark_as_template(self, vm_name):
        mobs.VirtualMachine.get(self.api, name=vm_name).MarkAsTemplate()  # Returns None

    def deploy_template(self, template, **kwargs):
        kwargs["power_on"] = True
        kwargs["template"] = False
        destination = kwargs.pop("vm_name")
        start_timeout = kwargs.pop("timeout", 900)
        self.clone_vm(template, destination, **kwargs)
        self.wait_vm_running(destination, num_sec=start_timeout)
        return destination

    def remove_host_from_cluster(self, host_name):
        host = mobs.HostSystem.get(self.api, name=host_name)
        task = host.DisconnectHost_Task()
        status, t = wait_for(self._task_wait, [task])

        if status != 'success':
            raise cfme_exc.HostNotRemoved("Host {} not removed: {}".format(
                host_name, task.info.error.localizedMessage))

        task = host.Destroy_Task()
        status, t = wait_for(self._task_wait, [task], fail_condition=None)

        return status == 'success'


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
        self.kwargs = kwargs

    @property
    def api(self):
        # test() will return false if the connection timeouts, catch it and force it to re-init
        try:
            if self._api is None or (self._api is not None and not self._api.test()):
                self._api = API(**self._api_kwargs)
        # if the connection was disconnected, force it to re-init
        except DisconnectedError:
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

    def current_ip_address(self, vm_name):
        info = self._get_vm(vm_name).get_guest_info()
        if info is None:
            return None
        try:
            return info.get_ips().get_ip()[0].get_address()
        except (AttributeError, IndexError):
            return None

    def get_ip_address(self, vm_name, timeout=600):
        try:
            return wait_for(lambda: self.current_ip_address(vm_name),
                fail_condition=None, delay=5, num_sec=timeout,
                message="get_ip_address from rhevm")[0]
        except TimedOutError:
            return None

    def get_vm_name_from_ip(self, ip):
        # unfortunately it appears you cannot query for ip address from the sdk,
        #   unlike curling rest api which does work
        """ Gets the name of a vm from its IP.

        Args:
            ip: The ip address of the vm.
        Returns: The vm name for the corresponding IP."""

        vms = self.api.vms.list()

        for vm in vms:
            print "Checking {}...".format(vm.name)
            if vm.get_guest_info() is None or vm.get_guest_info().get_ips() is None:
                continue
            else:
                for addr in vm.get_guest_info().get_ips().get_ip():
                    if ip in addr.get_address():
                        return vm.name
        raise cfme_exc.VmNotFoundViaIP('The requested IP is not known as a VM')

    def does_vm_exist(self, name):
        try:
            self._get_vm(name)
            return True
        except VMInstanceNotFound:
            return False

    def start_vm(self, vm_name=None):
        self.wait_vm_steady(vm_name, num_sec=300)
        logger.info(' Starting RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            logger.info(' RHEV VM %s os already running.' % vm_name)
            return True
        else:
            vm.start()
            self.wait_vm_running(vm_name)
            return True

    def stop_vm(self, vm_name):
        self.wait_vm_steady(vm_name, num_sec=300)
        logger.info(' Stopping RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            logger.info(' RHEV VM %s os already stopped.' % vm_name)
            return True
        else:
            vm.stop()
            self.wait_vm_stopped(vm_name)
            return True

    def delete_vm(self, vm_name):
        self.wait_vm_steady(vm_name, num_sec=300)
        vm = self._get_vm(vm_name)
        if not self.is_vm_stopped(vm_name):
            self.stop_vm(vm_name)
        logger.debug(' Deleting RHEV VM %s' % vm_name)
        vm.delete()
        wait_for(
            lambda: self.does_vm_exist(vm_name),
            fail_condition=True,
            message="wait for RHEV VM %s deleted" % vm_name,
            num_sec=300
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

    def vm_creation_time(self, vm_name):
        vm = self._get_vm(vm_name)
        return vm.get_creation_time().replace(tzinfo=None)

    def in_steady_state(self, vm_name):
        return self.vm_status(vm_name) in {"up", "down", "suspended"}

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) == "up"

    def wait_vm_running(self, vm_name, num_sec=360):
        logger.info(" Waiting for RHEV-M VM %s to change status to ON" % vm_name)
        wait_for(self.is_vm_running, [vm_name], num_sec=num_sec)

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) == "down"

    def wait_vm_stopped(self, vm_name, num_sec=360):
        logger.info(" Waiting for RHEV-M VM %s to change status to OFF" % vm_name)
        wait_for(self.is_vm_stopped, [vm_name], num_sec=num_sec)

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == "suspended"

    def wait_vm_suspended(self, vm_name, num_sec=720):
        logger.info(" Waiting for RHEV-M VM %s to change status to SUSPENDED" % vm_name)
        wait_for(self.is_vm_suspended, [vm_name], num_sec=num_sec)

    def suspend_vm(self, vm_name):
        self.wait_vm_steady(vm_name, num_sec=300)
        logger.debug(' Suspending RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            raise VMInstanceNotSuspended(vm_name)
        elif vm.status.get_state() == 'suspended':
            logger.info(' RHEV VM %s is already suspended.' % vm_name)
            return True
        else:
            vm.suspend()
            self.wait_vm_suspended(vm_name)
            return True

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')

    def deploy_template(self, template, *args, **kwargs):
        logger.debug(' Deploying RHEV template %s to VM %s' % (template, kwargs["vm_name"]))
        timeout = kwargs.pop('timeout', 900)
        vm_kwargs = {
            'name': kwargs['vm_name'],
            'cluster': self.api.clusters.get(kwargs['cluster']),
            'template': self.api.templates.get(template)
        }
        if 'placement_policy_host' in kwargs and 'placement_policy_affinity' in kwargs:
            host = params.Host(name=kwargs['placement_policy_host'])
            policy = params.VmPlacementPolicy(host=host,
                affinity=kwargs['placement_policy_affinity'])
            vm_kwargs['placement_policy'] = policy
        vm = params.VM(**vm_kwargs)
        self.api.vms.add(vm)
        self.wait_vm_stopped(kwargs['vm_name'], num_sec=timeout)
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
        self.kwargs = kwargs

    def disconnect(self):
        """Disconnect from the EC2 API -- NOOP

        AWS EC2 service is stateless, so there's nothing to disconnect from
        """
        pass

    def info(self):
        """Returns the current versions of boto and the EC2 API being used"""
        return '%s %s' % (boto.UserAgent, self.api.APIVersion)

    def list_vm(self):
        """Returns a list from instance IDs currently active on EC2 (not terminated)"""
        return [inst.id for inst in self._get_all_instances() if inst.state != 'terminated']

    def list_template(self):
        private_images = self.api.get_all_images(owners=['self'],
                                                 filters={'image-type': 'machine'})
        shared_images = self.api.get_all_images(executable_by=['self'],
                                                filters={'image-type': 'machine'})
        combined_images = list(set(private_images) | set(shared_images))
        # Try to pull the image name (might not exist), falling back on ID (must exist)
        return map(lambda i: i.name or i.id, combined_images)

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
        instance = self._get_instance(instance_id)
        return instance.state

    def vm_creation_time(self, instance_id):
        instance = self._get_instance(instance_id)
        # Example instance.launch_time: 2014-08-13T22:09:40.000Z
        launch_time = datetime.strptime(instance.launch_time[:19], '%Y-%m-%dT%H:%M:%S')
        # launch time is UTC, localize it, make it tz-naive to work with timedelta
        return local_tz.fromutc(launch_time).replace(tzinfo=None)

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

    def is_vm_state(self, instance_id, state):
        return self.vm_status(instance_id) in state

    def is_vm_running(self, instance_id):
        """Is the VM running?

        Args:
            instance_id: ID of the instance to inspect
        Returns: Whether or not the requested instance is running
        """
        return self.vm_status(instance_id) in self.states['running']

    def wait_vm_running(self, instance_id, num_sec=360):
        logger.info(" Waiting for EC2 instance %s to change status to running" % instance_id)
        wait_for(self.is_vm_running, [instance_id], num_sec=num_sec)

    def is_vm_stopped(self, instance_id):
        """Is the VM stopped?

        Args:
            instance_id: ID of the instance to inspect
        Returns: Whether or not the requested instance is stopped
        """
        return self.vm_status(instance_id) in self.states['stopped']

    def wait_vm_stopped(self, instance_id, num_sec=360):
        logger.info(
            " Waiting for EC2 instance %s to change status to stopped or terminated" % instance_id
        )
        wait_for(self.is_vm_stopped, [instance_id], num_sec=num_sec)

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

    def wait_vm_suspended(self, instance_id, num_sec):
        """We would wait forever - EC2 doesn't support this.

        Args:
            instance_id: ID of the instance to wait for
        Raises:
            ActionNotSupported: The action is not supported on the system
        """
        raise ActionNotSupported()

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')

    def deploy_template(self, template, *args, **kwargs):
        """Instantiate the requested template image (ami id)

        Accepts args/kwargs from boto's
        :py:meth:`run_instances<boto:boto.ec2.connection.EC2Connection.run_instances>` method

        Most important args are listed below.

        Args:
            template: Template name (AMI ID) to instantiate
            vm_name: Name of the instance (Name tag to set)
            instance_type: Type (flavor) of the instance

        Returns: Instance ID of the created instance

        Note: min_count and max_count args will be forced to '1'; if you're trying to do
              anything fancier than that, you might be in the wrong place

        """
        # Enforce create_vm only creating one VM
        logger.info(" Deploying EC2 template %s" % template)

        # strip out kwargs that ec2 doesn't understand
        timeout = kwargs.pop('timeout', 900)
        vm_name = kwargs.pop('vm_name', None)

        # Make sure we only provision one VM
        kwargs.update({'min_count': 1, 'max_count': 1})

        # sanity-check inputs
        if 'instance_type' not in kwargs:
            kwargs['instance_type'] = 'm1.small'
        if not template.startswith('ami'):
            # assume this is a lookup by name, get the ami id
            template = self._get_ami_id_by_name(template)

        # clone!
        reservation = self.api.run_instances(template, *args, **kwargs)
        instances = self._get_instances_from_reservations([reservation])
        # Should have only made one VM; return its ID for use in other methods
        self.wait_vm_running(instances[0].id, num_sec=timeout)

        if vm_name:
            self.set_name(instances[0].id, vm_name)
        return instances[0].id

    def set_name(self, instance_id, new_name):
        logger.info("Setting name of EC2 instance %s to %s" % (instance_id, new_name))
        instance = self._get_instance(instance_id)
        instance.add_tag('Name', new_name)
        return new_name

    def get_name(self, instance_id):
        return self._get_instance(instance_id).tags.get('Name', instance_id)

    def _get_instance(self, instance_id):
        instance_id = self._get_instance_id_by_name(instance_id)
        reservations = self.api.get_all_instances([instance_id])
        instances = self._get_instances_from_reservations(reservations)
        if len(instances) > 1:
            raise MultipleInstancesError

        try:
            return instances[0]
        except KeyError:
            return None

    def current_ip_address(self, instance_id):
        return str(self._get_instance(instance_id).ip_address)

    def get_ip_address(self, instance_id, **kwargs):
        return self.current_ip_address(instance_id)

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

        # We have an instance! return its ID
        return instances[0].id

    def _get_ami_id_by_name(self, image_name):
        matches = self.api.get_all_images(filters={'name': image_name})
        if not matches:
            raise ImageNotFoundError(image_name)
        elif len(matches) > 1:
            raise MultipleImagesError('Template name %s returned more than one image_name. '
                'Use the ami-ID or remove duplicates from EC2' % image_name)

        return matches[0].id

    def does_vm_exist(self, name):
        try:
            self._get_instance_id_by_name(name)
            return True
        except MultipleInstancesError:
            return True
        except VMInstanceNotFound:
            return False

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

        Takes an optional timeout value.
        """
        wait_for(lambda: self.vm_status(instance_id) in expected, num_sec=timeout)

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
        'num_vm': lambda self: self._num_vm_stat(),
        'num_template': lambda self: len(self.list_template()),
    }

    states = {
        'running': ('ACTIVE',),
        'stopped': ('SHUTOFF',),
        'suspended': ('SUSPENDED',),
    }

    can_suspend = True

    def __init__(self, **kwargs):
        self.tenant = kwargs['tenant']
        self.username = kwargs['username']
        self.password = kwargs['password']
        self.auth_url = kwargs['auth_url']
        self._api = None
        self._kapi = None

    def _num_vm_stat(self):
        if current_version() < '5.3':
            filter_tenants = False
        else:
            filter_tenants = True
        return len(self._get_all_instances(filter_tenants))

    @property
    def api(self):
        if not self._api:
            self._api = osclient.Client(self.username, self.password, self.tenant,
                                        self.auth_url, service_type="compute")
        return self._api

    @property
    def kapi(self):
        if not self._kapi:
            self._kapi = oskclient.Client(username=self.username, password=self.password,
                                          tenant_name=self.tenant, auth_url=self.auth_url)
        return self._kapi

    def _get_tenants(self):
        real_tenants = []
        tenants = self.kapi.tenants.list()
        for tenant in tenants:
            users = tenant.list_users()
            user_list = [user.name for user in users]
            if self.username in user_list:
                real_tenants.append(tenant)
        return real_tenants

    def _get_tenant(self, **kwargs):
        return self.kapi.tenants.find(**kwargs).id

    def _get_user(self, **kwargs):
        return self.kapi.users.find(**kwargs).id

    def _get_role(self, **kwargs):
        return self.kapi.roles.find(**kwargs).id

    def add_tenant(self, tenant_name, description=None, enabled=True, user=None, roles=None):
        tenant = self.kapi.tenants.create(tenant_name=tenant_name,
                                          description=description,
                                          enabled=enabled)
        if user and roles:
            user = self._get_user(name=user)
            for role in roles:
                role_id = self._get_role(name=role)
                tenant.add_user(user, role_id)
        return tenant.id

    def list_tenant(self):
        return [i.name for i in self._get_tenants()]

    def remove_tenant(self, tenant_name):
        tid = self._get_tenant(name=tenant_name)
        self.kapi.tenants.delete(tid)

    def start_vm(self, instance_name):
        logger.info(" Starting OpenStack instance %s" % instance_name)
        if self.is_vm_running(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        if self.is_vm_suspended(instance_name):
            instance.resume()
        else:
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

    def vm_creation_time(self, vm_name):
        instance = self._find_instance_by_name(vm_name)
        # Example vm.created: 2014-08-14T23:29:30Z
        create_time = datetime.strptime(instance.created, '%Y-%m-%dT%H:%M:%SZ')
        # create time is UTC, localize it, strip tzinfo
        return local_tz.fromutc(create_time).replace(tzinfo=None)

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) == 'ACTIVE'

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) == 'SHUTOFF'

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == 'SUSPENDED'

    def wait_vm_running(self, vm_name, num_sec=360):
        logger.info(" Waiting for OS instance %s to change status to ACTIVE" % vm_name)
        wait_for(self.is_vm_running, [vm_name], num_sec=num_sec)

    def wait_vm_stopped(self, vm_name, num_sec=360):
        logger.info(" Waiting for OS instance %s to change status to SHUTOFF" % vm_name)
        wait_for(self.is_vm_stopped, [vm_name], num_sec=num_sec)

    def wait_vm_suspended(self, vm_name, num_sec=720):
        logger.info(" Waiting for OS instance %s to change status to SUSPENDED" % vm_name)
        wait_for(self.is_vm_suspended, [vm_name], num_sec=num_sec)

    def suspend_vm(self, instance_name):
        logger.info(" Suspending OpenStack instance %s" % instance_name)
        if self.is_vm_suspended(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.suspend()
        wait_for(lambda: self.is_vm_suspended(instance_name), message="suspend %s" % instance_name)

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('clone_vm not implemented.')

    def deploy_template(self, template, *args, **kwargs):
        """ Deploys an OpenStack instance from a template.

        For all available args, see ``create`` method found here:
        http://docs.openstack.org/developer/python-novaclient/ref/v1_1/servers.html

        Most important args are listed below.

        Args:
            template: The name of the template to use.
            flavour_name: The name of the flavour to use.
            vm_name: A name to use for the vm.
            network_name: The name of the network if it is a multi network setup (Havanna).

        Note: If assign_floating_ip kwarg is present, then :py:meth:`OpenstackSystem.create_vm` will
            attempt to register a floating IP address from the pool specified in the arg.
        """
        nics = []
        timeout = kwargs.pop('timeout', 900)
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
        self.wait_vm_running(kwargs['vm_name'], num_sec=timeout)
        if kwargs.get('floating_ip_pool', None):
            ip = self.api.floating_ips.create(kwargs['floating_ip_pool'])
            instance.add_floating_ip(ip)

        return kwargs['vm_name']

    def _get_instance_networks(self, name):
        instance = self._find_instance_by_name(name)
        return instance._info['addresses']

    def current_ip_address(self, name):
        networks = self._get_instance_networks(name)
        for network_nics in networks.itervalues():
            for nic in network_nics:
                if nic['OS-EXT-IPS:type'] == 'floating':
                    return str(nic['addr'])

    def get_vm_name_from_ip(self, ip):
        # unfortunately it appears you cannot query for ip address from the sdk,
        #   unlike curling rest api which does work
        """ Gets the name of a vm from its IP.

        Args:
            ip: The ip address of the vm.
        Returns: The vm name for the corresponding IP."""

        instances = self._get_all_instances()

        for instance in instances:
            addr = self.get_ip_address(instance.name)
            if addr is not None and ip in addr:
                return str(instance.name)
        raise cfme_exc.VmNotFoundViaIP('The requested IP is not known as a VM')

    def get_ip_address(self, name, **kwargs):
        return self.current_ip_address(name)

    def _get_all_instances(self, filter_tenants=True):
        instances = self.api.servers.list(True, {'all_tenants': True})
        if filter_tenants:
            # Filter instances based on their tenant ID
            # needed for CFME 5.3 and higher
            tenants = self._get_tenants()
            ids = [tenant.id for tenant in tenants]
            instances = filter(lambda i: i.tenant_id in ids, instances)
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


class SCVMMSystem(MgmtSystemAPIBase):
    """This class is used to connect to M$ SCVMM

    It still has some drawback, the main one is that pywinrm does not support domains with simple
    auth mode so I have to do the connection manually in the script which seems to be VERY slow.
    """
    STATE_RUNNING = "Running"
    STATES_STOPPED = {"PowerOff", "Stopped"}  # TODO:  "Stopped" when using shutdown. Differ it?
    STATE_PAUSED = "Paused"
    STATES_STEADY = {STATE_RUNNING, STATE_PAUSED}
    STATES_STEADY.update(STATES_STOPPED)

    _stats_available = {
        'num_vm': lambda self: len(self.list_vm()),
        'num_template': lambda self: len(self.list_template()),
    }

    def __init__(self, **kwargs):
        self.host = kwargs["hostname"]
        self.user = kwargs["username"]
        self.password = kwargs["password"]
        self.domain = kwargs["domain"]
        self.api = winrm.Session(self.host, auth=(self.user, self.password))

    @property
    def pre_script(self):
        """Script that ensures we can access the SCVMM.

        Without domain used in login, it is not possible to access the SCVMM environment. Therefore
        we need to create our own authentication object (PSCredential) which will provide the
        domain. Then it works. Big drawback is speed of this solution.
        """
        return dedent("""
        $secpasswd = ConvertTo-SecureString "{}" -AsPlainText -Force
        $mycreds = New-Object System.Management.Automation.PSCredential ("{}\\{}", $secpasswd)
        $scvmm_server = Get-SCVMMServer -Computername localhost -Credential $mycreds
        """.format(self.password, self.domain, self.user))

    def run_script(self, script):
        """Wrapper for running powershell scripts. Ensures the ``pre_script`` is loaded."""
        script = dedent(script)
        logger.debug(" Running PowerShell script:\n{}\n".format(script))
        result = self.api.run_ps("{}\n\n{}".format(self.pre_script, script))
        if result.status_code != 0:
            raise self.PowerShellScriptError("Script returned {}!: {}"
                .format(result.status_code, result.std_err))
        return result.std_out.strip()

    def _do_vm(self, vm_name, action, params=""):
        logger.info(" {} {} SCVMM VM `{}`".format(action, params, vm_name))
        self.run_script(
            "Get-SCVirtualMachine -Name \"{}\" -VMMServer $scvmm_server | {}-SCVirtualMachine {}"
            .format(vm_name, action, params).strip())

    def start_vm(self, vm_name, force_start=False):
        """Start or resume virtual machine.

        Args:
            vm_name: Name of the virtual machine
            force_start: If we want to use the Start specifically and not Resume
        """
        if not force_start and self.is_vm_suspended(vm_name):
            # Resume
            self._do_vm(vm_name, "Resume")
        else:
            # Ordinary start
            self._do_vm(vm_name, "Start")

    def wait_vm_running(self, vm_name, num_sec=300):
        wait_for(
            lambda: self.is_vm_running(vm_name),
            message="SCVMM VM {} be running.".format(vm_name),
            num_sec=num_sec)

    def stop_vm(self, vm_name, shutdown=False):
        self._do_vm(vm_name, "Stop", "-Force" if not shutdown else "")

    def wait_vm_stopped(self, vm_name, num_sec=300):
        wait_for(
            lambda: self.is_vm_stopped(vm_name),
            message="SCVMM VM {} be stopped.".format(vm_name),
            num_sec=num_sec)

    def create_vm(self, vm_name):
        raise NotImplementedError('create_vm not implemented.')

    def delete_vm(self, vm_name):
        if not self.is_vm_stopped(vm_name):
            # Paused VM can be stopped too, so no special treatment here
            self.stop_vm(vm_name)
            self.wait_vm_stopped(vm_name)
        self._do_vm(vm_name, "Remove")

    def restart_vm(self, vm_name):
        self._do_vm(vm_name, "Reset")

    def list_vm(self, **kwargs):
        data = self.run_script(
            "Get-SCVirtualMachine -All -VMMServer $scvmm_server | "
            "where { $_.MarkedAsTemplate -eq $FALSE } | convertto-xml -as String")
        return etree.parse(StringIO(data)).getroot().xpath("./Object/Property[@Name='Name']/text()")

    def list_template(self):
        data = self.run_script(
            "Get-Template -VMMServer $scvmm_server | convertto-xml -as String")
        return etree.parse(StringIO(data)).getroot().xpath("./Object/Property[@Name='Name']/text()")

    def list_flavor(self):
        raise NotImplementedError('list_flavor not implemented.')

    def list_network(self):
        data = self.run_script(
            "Get-SCLogicalNetwork -VMMServer $scvmm_server | convertto-xml -as String")
        return etree.parse(StringIO(data)).getroot().xpath(
            "./Object/Property[@Name='Name']/text()")

    def info(self):
        pass

    def disconnect(self):
        pass

    def vm_status(self, vm_name):
        data = self.run_script(
            "Get-SCVirtualMachine -Name \"{}\" -VMMServer $scvmm_server | convertto-xml -as String"
            .format(vm_name))
        return etree.parse(StringIO(data)).getroot().xpath(
            "./Object/Property[@Name='StatusString']/text()")[0]

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) == self.STATE_RUNNING

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) in self.STATES_STOPPED

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == self.STATE_PAUSED

    def in_steady_state(self, vm_name):
        return self.vm_status(vm_name) in self.STATES_STEADY

    def suspend_vm(self, vm_name):
        self._do_vm(vm_name, "Suspend")

    def wait_vm_suspended(self, vm_name, num_sec=300):
        wait_for(
            lambda: self.is_vm_suspended(vm_name),
            message="SCVMM VM {} suspended.".format(vm_name),
            num_sec=num_sec)

    def clone_vm(self, source_name, vm_name):
        """It wants exact host and placement (c:/asdf/ghjk) :("""
        raise NotImplementedError('clone_vm not implemented.')

    def does_vm_exist(self, vm_name):
        result = self.run_script("Get-SCVirtualMachine -Name \"{}\" -VMMServer $scvmm_server"
            .format(vm_name)).strip()
        return len(result) > 0

    def deploy_template(self, template, vm_name=None, host_group=None, **bogus):
        script = """
        $tpl = Get-SCVMTemplate -Name "{template}" -VMMServer $scvmm_server
        $vmhostgroup = Get-SCVMHostGroup -Name "{host_group}" -VMMServer $scvmm_server
        $vmc = New-SCVMConfiguration -VMTemplate $tpl -Name "{vm_name}" -VMHostGroup $vmhostgroup
        Update-SCVMConfiguration -VMConfiguration $vmc
        New-SCVirtualMachine -Name "{vm_name}" -VMConfiguration $vmc #-VMMServer $scvmm_server
        """.format(template=template, vm_name=vm_name, host_group=host_group)
        logger.info(" Deploying SCVMM VM `{}` from template `{}` on host group `{}`"
            .format(vm_name, template, host_group))
        self.run_script(script)
        self.start_vm(vm_name)
        return vm_name

    def current_ip_address(self, vm_name):
        data = self.run_script(
            "Get-SCVirtualMachine -Name \"{}\" -VMMServer $scvmm_server |"
            "Get-SCVirtualNetworkAdapter | "
            "convertto-xml -as String")
        return etree.parse(StringIO(data)).getroot().xpath(
            "./Object/Property[@Name='IPv4Addresses']/text()")
        # TODO: Scavenge informations how these are formatted, I see no if-s in SCVMM

    def get_ip_address(self, vm_name, **kwargs):
        return self.current_ip_address(vm_name)

    def remove_host_from_cluster(self, hostname):
        """I did not notice any scriptlet that lets you do this."""

    def data(self, vm_name):
        """Returns detailed informations about SCVMM VM"""
        data = self.run_script(
            "Get-SCVirtualMachine -Name \"{}\" -VMMServer $scvmm_server | convertto-xml -as String"
            .format(vm_name))
        return self.SCVMMDataHolderDict(etree.parse(StringIO(data)).getroot().xpath("./Object")[0])

    ##
    # Classes and functions used to access detailed SCVMM Data
    @staticmethod
    def parse_data(t, data):
        if data is None:
            return None
        elif t == "System.Boolean":
            return data.lower().strip() == "true"
        elif t.startswith("System.Int"):
            return int(data)
        elif t == "System.String" and data.lower().strip() == "none":
            return None

    class SCVMMDataHolderDict(object):
        def __init__(self, data):
            for prop in data.xpath("./Property"):
                name = prop.attrib["Name"]
                t = prop.attrib["Type"]
                children = prop.getchildren()
                if children:
                    if prop.xpath("./Property[@Name]"):
                        self.__dict__[name] = self.SCVMMDataHolderDict(prop)
                    else:
                        self.__dict__[name] = self.SCVMMDataHolderList(prop)
                else:
                    data = prop.text
                    result = self.parse_data(t, prop.text)
                    self.__dict__[name] = result

        def __repr__(self):
            return repr(self.__dict__)

    class SCVMMDataHolderList(list):
        def __init__(self, data):
            super(SCVMMSystem.SCVMMDataHolderList, self).__init__()
            for prop in data.xpath("./Property"):
                t = prop.attrib["Type"]
                data = prop.text
                result = self.parse_data(t, prop.text)
                self.append(result)

    class PowerShellScriptError(Exception):
        pass


class ActionNotSupported(Exception):
    """Raised when an action is not supported."""
    pass


class ActionTimedOutError(Exception):
    pass


class ImageNotFoundError(Exception):
    pass


class MultipleImagesError(Exception):
    pass


class MultipleInstancesError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class NetworkNameNotFound(Exception):
    pass


class VMInstanceNotCloned(Exception):
    """Raised if a VM or instance is not found."""
    def __init__(self, template):
        self.template = template

    def __str__(self):
        return 'Could not clone %s' % self.template


class VMInstanceNotFound(Exception):
    """Raised if a VM or instance is not found."""
    def __init__(self, vm_name):
        self.vm_name = vm_name

    def __str__(self):
        return 'Could not find a VM/instance named %s.' % self.vm_name


class VMInstanceNotSuspended(Exception):
    """Raised if a VM or instance is not able to be suspended."""
    def __init__(self, vm_name):
        self.vm_name = vm_name

    def __str__(self):
        return 'Could not suspend %s because it\'s not running.' % self.vm_name
