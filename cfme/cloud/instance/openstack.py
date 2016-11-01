from utils import version, deferred_verpick
from cfme.exceptions import OptionNotAvailable
from cfme.web_ui import fill, flash
from cfme.fixtures import pytest_selenium as sel
from cfme.common.vm import VM
from . import Instance, select_provision_image


@VM.register_for_provider_type("openstack")
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

    # CFME power states
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_ERROR = "non-operational"
    STATE_PAUSED = "paused"
    STATE_SUSPENDED = "suspended"
    STATE_UNKNOWN = "unknown"
    STATE_ARCHIVED = "archived"
    STATE_TERMINATED = "terminated"

    def create(self, email=None, first_name=None, last_name=None, cloud_network=None,
               instance_type=None, cancel=False, **prov_fill_kwargs):
        """Provisions an OpenStack instance with the given properties through CFME

        Args:
            email: Email of the requester
            first_name: Name of the requester
            last_name: Surname of the requester
            cloud_network: Name of the cloud network the instance should belong to
            instance_type: Type of the instance
            cancel: Clicks the cancel button if `True`, otherwise clicks the submit button
                    (Defaults to `False`)
        Note:
            For more optional keyword arguments, see
            :py:data:`cfme.cloud.provisioning.provisioning_form`
        """
        from cfme.provisioning import provisioning_form
        # Nav to provision form and select image
        select_provision_image(template_name=self.template_name, provider=self.provider)

        # not supporting multiselect now, just take first value
        security_groups = prov_fill_kwargs.pop('security_groups', None)
        if security_groups:
            prov_fill_kwargs['security_groups'] = security_groups[0]

        fill(provisioning_form, dict(
            email=email,
            first_name=first_name,
            last_name=last_name,
            instance_name=self.name,
            instance_type=instance_type,
            cloud_network=cloud_network,
            **prov_fill_kwargs
        ))

        if cancel:
            sel.click(provisioning_form.cancel_button)
            flash.assert_success_message(
                "Add of new VM Provision Request was cancelled by the user")
        else:
            sel.click(provisioning_form.submit_button)
            flash.assert_success_message(
                "VM Provision Request was Submitted, you will be notified when your VMs are ready")

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
        elif option == OpenStackInstance.RESUME:
            self.provider.mgmt.resume_vm(self.name)
        elif option == OpenStackInstance.PAUSE:
            self.provider.mgmt.pause_vm(self.name)
        elif option == OpenStackInstance.UNPAUSE:
            self.provider.mgmt.unpause_vm(self.name)
        elif option == OpenStackInstance.RESTART:
            self.provider.mgmt.restart_vm(self.name)
        elif option == OpenStackInstance.TERMINATE:
            self.provider.mgmt.delete_vm(self.name)
        else:
            raise OptionNotAvailable(option + " is not a supported action")
