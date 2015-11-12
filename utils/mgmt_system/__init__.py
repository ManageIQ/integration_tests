# Imports for backward compatility and convenience
# NOQA all the things because
import time
from mgmtsystem.base import VMInfo, MgmtSystemAPIBase, ContainerMgmtSystemAPIBase, Logger  # NOQA
from mgmtsystem import exceptions  # NOQA
from mgmtsystem.ec2 import EC2System  # NOQA
from mgmtsystem.openstack import OpenstackSystem  # NOQA
from mgmtsystem.rhevm import RHEVMSystem as RHEVMSystemBase  # NOQA
from mgmtsystem.scvmm import SCVMMSystem  # NOQA
from mgmtsystem.virtualcenter import VMWareSystem  # NOQA
from kubernetes import Kubernetes  # NOQA
from openshift import Openshift  # NOQA

from utils import conf
from utils.log import logger
from utils.ssh import SSHClient

# Temporary
from openstack_infra import OpenstackInfraSystem  # NOQA

# Overrides

from ovirtsdk.xml import params


class RHEVMSystem(RHEVMSystemBase):

    def start_vm(self, vm_name=None, **kwargs):
        self.wait_vm_steady(vm_name)
        self.logger.info(' Starting RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            self.logger.info(' RHEV VM %s os already running.' % vm_name)
            return True
        else:
            if 'initialization' in kwargs:
                vm.start(kwargs['initialization'])
            else:
                vm.start()
            self.wait_vm_running(vm_name)
            return True

    def deploy_template(self, template, *args, **kwargs):
        self.logger.debug(' Deploying RHEV template %s to VM %s' % (template, kwargs["vm_name"]))
        timeout = kwargs.pop('timeout', 900)
        power_on = kwargs.pop('power_on', True)
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
        if power_on:
            version = self.api.get_product_info().get_full_version()
            if template.startswith("cfme-55") and version.startswith("3.4"):
                action = params.Action(vm=params.VM(initialization=params.Initialization(
                    cloud_init=params.CloudInit(users=params.Users(
                        user=[params.User(user_name="root", password="smartvm")])))))
                ciargs = {}
                ciargs['initialization'] = action
                self.start_vm(vm_name=kwargs['vm_name'], **ciargs)
            else:
                self.start_vm(vm_name=kwargs['vm_name'])
        return kwargs['vm_name']

    def connect_direct_lun_to_appliance(self, vm_name, disconnect):
        """Connects or disconnects the direct lun disk to an appliance.

        Args:
            vm_name: Name of the VM with the appliance.
            disconnect: If False, it will connect, otherwise it will disconnect
        """
        if "provider_key" in self.kwargs:
            provider_name = self.kwargs["provider_key"]
        else:
            raise TypeError("provider_key not supplied to the provider.")
        # check that the vm exists on the rhev provider, get the ip address if so
        try:
            vm = self.api.vms.get(vm_name)
            ip_addr = self.get_ip_address(vm_name)
        except:
            raise NameError("{} not found on  {}".format(vm_name, provider_name))

        # check for direct lun definition on provider's cfme_data.yaml
        if 'direct_lun' not in self.kwargs:
            raise ValueError(
                "direct_lun key not in cfme_data.yaml under provider {}, exiting...".format(
                    provider_name))

        # does the direct lun exist
        prov_data = self.kwargs
        dlun_name = prov_data['direct_lun']['name']
        dlun = self.api.disks.get(dlun_name)
        if dlun is None:

            #    Create the iSCSI storage connection:
            sc = params.StorageConnection()
            sc.set_address(prov_data['direct_lun']['ip_address'])
            sc.set_type("iscsi")
            sc.set_port(int(prov_data['direct_lun']['port']))
            sc.set_target(prov_data['direct_lun']['iscsi_target'])

            #    Add the direct LUN disk:
            lu = params.LogicalUnit()
            lu.set_id(prov_data['direct_lun']['iscsi_target'])
            lu.set_address(sc.get_address())
            lu.set_port(sc.get_port())
            lu.set_target(sc.get_target())
            storage = params.Storage()
            storage.set_type("iscsi")
            storage.set_logical_unit([lu])
            disk = params.Disk()
            disk.set_name(dlun_name)
            disk.set_interface("virtio")
            disk.set_type("iscsi")
            disk.set_format("raw")
            disk.set_lun_storage(storage)
            disk.set_shareable(True)
            disk = self.api.disks.add(disk)
            dlun = self.api.disks.get(dlun_name)

        # add it
        if not disconnect:
            retries = 0
            while retries < 3:
                retries += 1
                direct_lun = params.Disk(id=dlun.id)
                try:
                    # is the disk present and active?
                    vm_disk_list = vm.get_disks().list()
                    for vm_disk in vm_disk_list:
                        if vm_disk.name == dlun_name:
                            if vm_disk.active:
                                return
                            else:
                                vm_disk.activate()
                                return

                    # if not present, add it and activate
                    direct_lun = params.Disk(id=dlun.id)
                    added_lun = vm.disks.add(direct_lun)
                    added_lun.activate()
                except Exception as e:
                    logger.error("Exception caught: %s" % str(e))
                    if retries == 3:
                        logger.error("exhausted retries and giving up")
                        raise
                    else:
                        logger.info("sleeping for 30s and retrying to connect direct lun")
                        time.sleep(30)

            # Init SSH client, run pvscan on the appliance
            ssh_kwargs = {
                'username': conf.credentials['ssh']['username'],
                'password': conf.credentials['ssh']['password'],
                'hostname': ip_addr
            }
            client = SSHClient(**ssh_kwargs)
            status, out = client.run_command('pvscan', timeout=5 * 60)

        # remove it
        else:
            vm_dlun = vm.disks.get(name=dlun_name)
            if vm_dlun is None:
                return
            else:
                detach = params.Action(detach=True)
                vm_dlun.delete(action=detach)
