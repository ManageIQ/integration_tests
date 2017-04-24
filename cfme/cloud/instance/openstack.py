# -*- coding: utf-8 -*-
from cfme.exceptions import OptionNotAvailable
from utils import version, deferred_verpick
from . import Instance


class OpenStackInstance(Instance):
    # CFME & provider power control options
    START = "Start"  # START also covers RESUME and UNPAUSE (same as in CFME 5.4+ web UI)
    POWER_ON = START  # For compatibility with the infra objects.
    SUSPEND = "Suspend"
    DELETE = "Delete"
    TERMINATE = deferred_verpick({
        version.LOWEST: 'Terminate',
        '5.6.1': 'Delete',
    })
    # CFME-only power control options
    SOFT_REBOOT = "Soft Reboot"
    HARD_REBOOT = "Hard Reboot"
    # Provider-only power control options
    STOP = "Stop"
    PAUSE = "Pause"
    RESTART = "Restart"
    SHELVE = "Shelve"
    SHELVE_OFFLOAD = "Shelve Offload"

    # CFME power states
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_ERROR = "non-operational"
    STATE_PAUSED = "paused"
    STATE_SUSPENDED = "suspended"
    STATE_REBOOTING = "reboot_in_progress"
    STATE_SHELVED = "shelved"
    STATE_SHELVED_OFFLOAD = "shelved_offloaded"
    STATE_UNKNOWN = "unknown"
    STATE_ARCHIVED = "archived"
    STATE_TERMINATED = "terminated"

    @property
    def ui_powerstates_available(self):
        return {
            'on': [self.SUSPEND, self.SOFT_REBOOT, self.HARD_REBOOT, self.TERMINATE],
            'off': [self.START, self.TERMINATE]}

    @property
    def ui_powerstates_unavailable(self):
        return {
            'on': [self.START],
            'off': [self.SUSPEND, self.SOFT_REBOOT, self.HARD_REBOOT]}

    def create(self, cancel=False, **prov_fill_kwargs):
        """Provisions an OpenStack instance with the given properties through CFME

        Args:
            cancel: Clicks the cancel button if `True`, otherwise clicks the submit button
                    (Defaults to `False`)
            prov_fill_kwargs: dictionary of provisioning field/value pairs
        Note:
            For more optional keyword arguments, see
            :py:data:`cfme.cloud.provisioning.ProvisioningForm`
        """
        super(OpenStackInstance, self).create(form_values=prov_fill_kwargs, cancel=cancel)

    def power_control_from_provider(self, option):
        """Power control the instance from the provider

        Args:
            option: power control action to take against instance

        Raises:
            OptionNotAvailable: option param must have proper value
        """
        if option == OpenStackInstance.START:
            self.provider.mgmt.start_vm(self.name)
        elif option == OpenStackInstance.STOP:
            self.provider.mgmt.stop_vm(self.name)
        elif option == OpenStackInstance.SUSPEND:
            self.provider.mgmt.suspend_vm(self.name)
        elif option == OpenStackInstance.PAUSE:
            self.provider.mgmt.pause_vm(self.name)
        elif option == OpenStackInstance.SHELVE:
            # TODO: rewrite it once mgmtsystem will get shelve
            # and shelve_offload methods
            self.provider.mgmt._find_instance_by_name(self.name).shelve()
        elif option == OpenStackInstance.SHELVE_OFFLOAD:
            self.provider.mgmt._find_instance_by_name(self.name).shelve_offload()
        elif option == OpenStackInstance.RESTART:
            self.provider.mgmt.restart_vm(self.name)
        elif option == OpenStackInstance.TERMINATE:
            self.provider.mgmt.delete_vm(self.name)
        else:
            raise OptionNotAvailable(option + " is not a supported action")
