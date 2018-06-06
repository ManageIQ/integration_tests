# -*- coding: utf-8 -*-
import attr
from riggerlib import recursive_update

from cfme.exceptions import OptionNotAvailable
from . import Instance, InstanceCollection


@attr.s
class GCEInstance(Instance):
    # CFME & provider power control options
    START = "Start"
    POWER_ON = START  # For compatibility with the infra objects.
    STOP = "Stop"
    DELETE = "Delete"
    TERMINATE = 'Delete'
    # CFME-only power control options
    SOFT_REBOOT = "Soft Reboot"
    # Provider-only power control options
    RESTART = "Restart"

    # CFME power states
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_SUSPENDED = "suspended"
    STATE_TERMINATED = "terminated"
    STATE_ARCHIVED = "archived"
    STATE_UNKNOWN = "unknown"

    @property
    def ui_powerstates_available(self):
        return {
            'on': [self.STOP, self.SOFT_REBOOT, self.TERMINATE],
            'off': [self.START, self.TERMINATE]}

    @property
    def ui_powerstates_unavailable(self):
        return {
            'on': [self.START],
            'off': [self.STOP, self.SOFT_REBOOT]}

    def power_control_from_provider(self, option):
        """Power control the instance from the provider

        Args:
            option: power control action to take against instance
        Raises:
            OptionNotAvailable: option param must have proper value
        """
        if option == GCEInstance.START:
            self.provider.mgmt.start_vm(self.name)
        elif option == GCEInstance.STOP:
            self.provider.mgmt.stop_vm(self.name)
        elif option == GCEInstance.RESTART:
            self.provider.mgmt.restart_vm(self.name)
        elif option == GCEInstance.TERMINATE:
            self.provider.mgmt.delete_vm(self.name)
        else:
            raise OptionNotAvailable(option + " is not a supported action")

    @property
    def vm_default_args(self):
        """Represents dictionary used for Vm/Instance provision with GCE mandatory default args"""
        inst_args = super(GCEInstance, self).vm_default_args
        provisioning = self.provider.data['provisioning']
        inst_args['properties']['boot_disk_size'] = provisioning.get('boot_disk_size', '10 GB')
        return inst_args

    @property
    def vm_default_args_rest(self):
        inst_args = super(GCEInstance, self).vm_default_args_rest
        provisioning = self.provider.data['provisioning']
        recursive_update(inst_args, {
            'vm_fields': {
                'boot_disk_size': provisioning['boot_disk_size'].replace(' ', '.')}})
        return inst_args


@attr.s
class GCEInstanceCollection(InstanceCollection):
    ENTITY = GCEInstance
