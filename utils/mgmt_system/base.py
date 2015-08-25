# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from contextlib import contextmanager

from utils.log import logger
from utils.wait import wait_for, TimedOutError


VMInfo = namedtuple("VMInfo", ["uuid", "name", "power_state", "ip"])


class MgmtSystemAPIBase(object):
    """Base interface class for Management Systems

    Interface notes:

    * Initializers of subclasses must support \*\*kwargs in their
      signtures
    * Action methods (start/stop/etc) should block until the requested
      action is complete

    """
    __metaclass__ = ABCMeta
    STEADY_WAIT_MINS = 3

    # Flags to indicate whether or not this MgmtSystem can suspend/pause,
    can_suspend = True
    can_pause = False

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
        raise NotImplementedError('remove_host_from_cluster not implemented.')

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
        return (self.is_vm_running(vm_name) or self.is_vm_stopped(vm_name) or
            self.is_vm_suspended(vm_name))

    def wait_vm_steady(self, vm_name):
        """Waits 2 (or user-specified time) minutes for VM to settle in steady state

        Args:
            vm_name: VM name
        """
        try:
            return wait_for(
                lambda: self.in_steady_state(vm_name),
                num_sec=self.STEADY_WAIT_MINS * 60,
                delay=2,
                message="VM %s in steady state" % vm_name
            )
        except TimedOutError:
            logger.exception("VM {} got stuck in {} state when waiting for steady state.".format(
                vm_name, self.vm_status(vm_name)))
            raise

    @property
    def can_rename(self):
        return hasattr(self, "rename_vm")

    @contextmanager
    def steady_wait(self, minutes):
        """Overrides original STEADY_WAIT_MINS variable in the object.

        This is useful eg. when creating templates in RHEV as it has long Image Locked period

        Args:
            minutes: How many minutes to wait
        """
        original = None
        if "STEADY_WAIT_MINS" in self.__dict__:
            original = self.__dict__["STEADY_WAIT_MINS"]
        self.__dict__["STEADY_WAIT_MINS"] = minutes
        yield
        if original is None:
            del self.__dict__["STEADY_WAIT_MINS"]
        else:
            self.__dict__["STEADY_WAIT_MINS"] = original

    def does_template_exist(self, template_name):
        """If system does not implement anything better, this will work """
        return template_name in self.list_template()

    def delete_template(self, template_name):
        return self.delete_vm(template_name)  # Fall back to original vSphere behaviour


class ContainerMgmtSystemAPIBase(MgmtSystemAPIBase):
    """Base interface class for Container Management Systems

    Interface notes:

    * Initializers of subclasses must support \*\*kwargs in their
      signtures
    * Action methods (start/stop/etc) should block until the requested
      action is complete

    """

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('clone_vm not implemented.')

    def create_vm(self, vm_name):
        raise NotImplementedError('create_vm not implemented.')

    def current_ip_address(self, vm_name):
        raise NotImplementedError('current_ip_address not implemented.')

    def delete_vm(self, vm_name):
        raise NotImplementedError('delete_vm not implemented.')

    def deploy_template(self, template, *args, **kwargs):
        raise NotImplementedError('deploy_template not implemented.')

    def disconnect(self):
        raise NotImplementedError('disconnect not implemented.')

    def does_vm_exist(self, name):
        raise NotImplementedError('does_vm_exist not implemented.')

    def get_ip_address(self, vm_name):
        raise NotImplementedError('get_ip_address not implemented.')

    def is_vm_running(self, vm_name):
        raise NotImplementedError('is_vm_running not implemented.')

    def is_vm_stopped(self, vm_name):
        raise NotImplementedError('is_vm_stopped not implemented.')

    def is_vm_suspended(self, vm_name):
        raise NotImplementedError('is_vm_suspended not implemented.')

    def list_flavor(self):
        raise NotImplementedError('list_flavor not implemented.')

    def list_template(self):
        raise NotImplementedError('list_template not implemented.')

    def list_vm(self, **kwargs):
        raise NotImplementedError('list_vm not implemented.')

    def remove_host_from_cluster(self, hostname):
        raise NotImplementedError('remove_host_from_cluster not implemented.')

    def restart_vm(self, vm_name):
        raise NotImplementedError('restart_vm not implemented.')

    def start_vm(self, vm_name):
        raise NotImplementedError('start_vm not implemented.')

    def stop_vm(self, vm_name):
        raise NotImplementedError('stop_vm not implemented.')

    def suspend_vm(self, vm_name):
        raise NotImplementedError('restart_vm not implemented.')

    def vm_status(self, vm_name):
        raise NotImplementedError('vm_status not implemented.')

    def wait_vm_running(self, vm_name, num_sec):
        raise NotImplementedError('wait_vm_running not implemented.')

    def wait_vm_stopped(self, vm_name, num_sec):
        raise NotImplementedError('wait_vm_stopped not implemented.')

    def wait_vm_suspended(self, vm_name, num_sec):
        raise NotImplementedError('wait_vm_suspended not implemented.')
