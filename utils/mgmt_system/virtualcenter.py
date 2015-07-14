# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""
import re
from datetime import datetime
from functools import partial
import operator

import time
from psphere import managedobjects as mobs
from psphere.client import Client
from psphere.errors import ObjectNotFoundError
from suds import WebFault

from cfme import exceptions as cfme_exc
from utils.log import logger
from utils.mgmt_system.base import MgmtSystemAPIBase, VMInfo
from utils.mgmt_system.exceptions import VMInstanceNotCloned, VMInstanceNotSuspended
from utils.version import Version
from utils.wait import wait_for, TimedOutError


class _PsphereClient(Client):

    def __init__(self, *args, **kwargs):
        self._cached_retry = dict()
        super(_PsphereClient, self).__init__(*args, **kwargs)

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

    def __getattribute__(self, attr):
        # fetch the attribute using parent class to avoid recursion
        res = super(_PsphereClient, self).__getattribute__(attr)
        # any callable (except 'login') is protected against unexpected logout
        if callable(res) and attr not in ('login', '_login_retry_wrapper'):
            if attr not in self._cached_retry:
                self._cached_retry[attr] = self._login_retry_wrapper(res)
            return self._cached_retry[attr]
        # don't mess with non-callables - just return them
        return res

    def _login_retry_wrapper(self, o):
        # tries to log in on failure
        def f(*args, **kwargs):
            try:
                return o(*args, **kwargs)
            except ObjectNotFoundError:
                try:
                    self.logout()
                except WebFault:
                    # Server raíses the following when we try to logout with an old session
                    # WebFault: Server raised fault: 'The session is not authenticated.'
                    pass
                logger.debug("{} disconnected (psphere api); logging back in and trying again"
                    .format(self.server))
                self.login()
                return o(*args, **kwargs)
        return f


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
        return Version(self.api.si.content.about.version)

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

    def all_vms(self):
        property_spec = self.api.create('PropertySpec')
        property_spec.all = False
        property_spec.pathSet = ['name', 'config.template']
        property_spec.type = 'VirtualMachine'
        pfs = self.api.get_search_filter_spec(self.api.si.content.rootFolder, property_spec)
        object_contents = self.api.si.content.propertyCollector.RetrieveProperties(specSet=[pfs])
        result = []
        for vm in object_contents:
            vm_props = {p.name: p.val for p in vm.propSet}
            if vm_props.get('config.template'):
                continue
            try:
                ip = str(vm.obj.summary.guest.ipAddress)
            except AttributeError:
                ip = None
            try:
                uuid = str(vm.obj.summary.config.uuid)
            except AttributeError:
                uuid = None
            result.append(
                VMInfo(
                    uuid,
                    str(vm.obj.summary.config.name),
                    str(vm.obj.summary.runtime.powerState),
                    ip,
                )
            )
        return result

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

    def rename_vm(self, vm_name, new_vm_name):
        vm = self._get_vm(vm_name)
        task = vm.Rename_Task(newName=new_vm_name)
        # Cycle until the new named vm is found
        # That must happen or the error state can come up too
        while not self.does_vm_exist(new_vm_name):
            task.update()
            if task.info.state == "error":
                return vm_name  # Old vm name if error
            time.sleep(0.5)
        else:
            # The newly renamed VM is found
            return new_vm_name

    @staticmethod
    def _progress_log_callback(source, destination, progress):
        logger.info("Provisioning progress {}->{}: {}".format(source, destination, str(progress)))

    def _pick_datastore(self, allowed_datastores):
        # Pick a datastore by space
        possible_datastores = [
            ds for ds in mobs.Datastore.all(self.api)
            if ds.name in allowed_datastores and ds.summary.accessible
            and ds.summary.multipleHostAccess and ds.overallStatus != "red"]
        possible_datastores.sort(
            key=lambda ds: float(ds.summary.freeSpace) / float(ds.summary.capacity),
            reverse=True)
        if not possible_datastores:
            raise Exception("No possible datastores!")
        return possible_datastores[0]

    def clone_vm(self, source, destination, resourcepool=None, datastore=None, power_on=True,
                 sparse=False, template=False, provision_timeout=1800, progress_callback=None,
                 allowed_datastores=None):
        try:
            if mobs.VirtualMachine.get(self.api, name=destination).name == destination:
                raise Exception("VM already present!")
        except ObjectNotFoundError:
            pass

        if progress_callback is None:
            progress_callback = partial(self._progress_log_callback, source, destination)

        source_template = mobs.VirtualMachine.get(self.api, name=source)

        vm_clone_spec = self.api.create("VirtualMachineCloneSpec")
        vm_reloc_spec = self.api.create("VirtualMachineRelocateSpec")
        # DATASTORE
        if isinstance(datastore, basestring):
            vm_reloc_spec.datastore = mobs.Datastore.get(self.api, name=datastore)
        elif isinstance(datastore, mobs.Datastore):
            vm_reloc_spec.datastore = datastore
        elif datastore is None:
            if allowed_datastores is not None:
                # Pick a datastore by space
                vm_reloc_spec.datastore = self._pick_datastore(allowed_datastores)
            else:
                # Use the same datastore
                datastores = source_template.datastore
                if isinstance(datastores, (list, tuple)):
                    vm_reloc_spec.datastore = datastores[0]
                else:
                    vm_reloc_spec.datastore = datastores
        else:
            raise NotImplementedError("{} not supported for datastore".format(datastore))
        progress_callback("Picked datastore `{}`".format(vm_reloc_spec.datastore.name))

        # RESOURCE POOL
        if isinstance(resourcepool, mobs.ResourcePool):
            vm_reloc_spec.pool = resourcepool
        else:
            vm_reloc_spec.pool = self._get_resource_pool(resourcepool)
        progress_callback("Picked resource pool `{}`".format(vm_reloc_spec.pool.name))

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

        progress_callback("Picked folder `{}`".format(folder.name))

        task = source_template.CloneVM_Task(folder=folder, name=destination, spec=vm_clone_spec)

        def _check():
            try:
                progress_callback("{}/{}%".format(task.info.state, task.info.progress))
            except AttributeError:
                pass
            return task.info.state not in {"queued", "running"}

        wait_for(
            _check,
            fail_func=task.update, num_sec=provision_timeout, delay=4
        )
        if task.info.state != 'success':
            logger.error('Clone VM failed: {}'.format(task.info.error.localizedMessage))
            raise VMInstanceNotCloned(source)
        else:
            return destination

    def mark_as_template(self, vm_name, **kwargs):
        mobs.VirtualMachine.get(self.api, name=vm_name).MarkAsTemplate()  # Returns None

    def deploy_template(self, template, **kwargs):
        kwargs["power_on"] = kwargs.pop("power_on", True)
        kwargs["template"] = False
        destination = kwargs.pop("vm_name")
        start_timeout = kwargs.pop("timeout", 1800)
        self.clone_vm(template, destination, **kwargs)
        if kwargs["power_on"]:
            self.wait_vm_running(destination, num_sec=start_timeout)
        else:
            self.wait_vm_stopped(destination, num_sec=start_timeout)
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
