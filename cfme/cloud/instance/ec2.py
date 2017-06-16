# -*- coding: utf-8 -*-
from cfme.exceptions import OptionNotAvailable
from . import Instance


class EC2Instance(Instance):
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

    def create(self, cancel=False, **prov_fill_kwargs):
        """Provisions an EC2 instance with the given properties through CFME

        Args:
            cancel: Clicks the cancel button if `True`, otherwise clicks the submit button
                    (Defaults to `False`)
            prov_fill_kwargs: dictionary of provisioning field/value pairs
        Note:
            For more optional keyword arguments, see
            :py:data:`cfme.cloud.provisioning.ProvisioningForm`
        """
        super(EC2Instance, self).create(form_values=prov_fill_kwargs, cancel=cancel)

    def power_control_from_provider(self, option):
        """Power control the instance from the provider

        Args:
            option: power control action to take against instance

        Raises:
            OptionNotAvailable: option param must have proper value
        """
        if option == EC2Instance.START:
            self.provider.mgmt.start_vm(self.name)
        elif option == EC2Instance.STOP:
            self.provider.mgmt.stop_vm(self.name)
        elif option == EC2Instance.RESTART:
            self.provider.mgmt.restart_vm(self.name)
        elif option == EC2Instance.TERMINATE:
            self.provider.mgmt.delete_vm(self.name)
        else:
            raise OptionNotAvailable(option + " is not a supported action")
