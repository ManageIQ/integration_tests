# -*- coding: utf-8 -*-
from cfme.exceptions import OptionNotAvailable
from cfme.utils import version, deferred_verpick
from cfme.utils.log import logger

from . import Instance


class AzureInstance(Instance):
    # CFME & provider power control options Added by Jeff Teehan on 5-16-2016
    START = "Start"
    POWER_ON = START  # For compatibility with the infra objects.
    STOP = "Stop"
    SUSPEND = "Suspend"
    DELETE = "Delete"
    TERMINATE = deferred_verpick({
        version.LOWEST: 'Terminate',
        '5.6.1': 'Delete',
    })
    # CFME-only power control options
    SOFT_REBOOT = "Soft Reboot"
    HARD_REBOOT = "Hard Reboot"  # unsupported by azure, used for negative tests
    # Provider-only power control options
    RESTART = "Restart"

    # CFME power states
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_SUSPENDED = "suspended"
    STATE_TERMINATED = "terminated"
    STATE_UNKNOWN = "unknown"
    STATE_ARCHIVED = "archived"

    @property
    def ui_powerstates_available(self):
        return {
            'on': [self.STOP, self.SUSPEND, self.SOFT_REBOOT, self.TERMINATE],
            'off': [self.START, self.TERMINATE]}

    @property
    def ui_powerstates_unavailable(self):
        return {
            'on': [self.START],
            'off': [self.STOP, self.SUSPEND, self.SOFT_REBOOT]}

    def create(self, cancel=False, **prov_fill_kwargs):
        """Provisions an Azure instance with the given properties through CFME

        Args:
            cancel: Clicks the cancel button if `True`, otherwise clicks the submit button
                    (Defaults to `False`)
            prov_fill_kwargs: dictionary of provisioning field/value pairs
        Note:
            For more optional keyword arguments, see
            :py:data:`cfme.cloud.provisioning.ProvisioningForm`
        """
        super(AzureInstance, self).create(form_values=prov_fill_kwargs, cancel=cancel)

    def power_control_from_provider(self, option):
        """Power control the instance from the provider

        Args:
            option: power control action to take against instance

        Raises:
            OptionNotAvailable: option param must have proper value
        """
        if option == AzureInstance.START:
            self.provider.mgmt.start_vm(self.name)
        elif option == AzureInstance.STOP:
            self.provider.mgmt.stop_vm(self.name)
        elif option == AzureInstance.RESTART:
            self.provider.mgmt.restart_vm(self.name)
        elif option == AzureInstance.SUSPEND:
            self.provider.mgmt.suspend_vm(self.name)
        elif option == AzureInstance.TERMINATE:
            self.provider.mgmt.delete_vm(self.name)
        else:
            raise OptionNotAvailable(option + " is not a supported action")

    def cleanup_on_provider(self):
        """
        Clean up a VM on an azure provider.

        Runs VM.cleanup_on_provider() to delete the VM, then also deletes NICs/PIPs associated
        with the VM. Exceptions raised are logged only.
        """
        super(AzureInstance, self).cleanup_on_provider()
        logger.info("cleanup: removing NICs/PIPs for VM '{}'".format(self.name))
        try:
            self.provider.mgmt.remove_nics_by_search(self.name, self.provider.mgmt.resource_group)
            self.provider.mgmt.remove_pips_by_search(self.name, self.provider.mgmt.resource_group)
        except Exception:
            logger.exception("cleanup: failed to cleanup NICs/PIPs for VM '{}'".format(self.name))
