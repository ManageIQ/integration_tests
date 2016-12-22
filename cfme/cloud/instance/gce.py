from utils import version, deferred_verpick
from cfme.exceptions import OptionNotAvailable
from cfme.web_ui import fill, flash
from cfme.fixtures import pytest_selenium as sel
from cfme.common.vm import VM
from . import Instance, select_provision_image


@VM.register_for_provider_type("gce")
class GCEInstance(Instance):
    # CFME & provider power control options
    START = "Start"
    POWER_ON = START  # For compatibility with the infra objects.
    STOP = "Stop"
    DELETE = "Delete"
    TERMINATE = deferred_verpick({
        version.LOWEST: 'Terminate',
        '5.6.1': 'Delete',
    })
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

    def create(self, email=None, first_name=None, last_name=None, availability_zone=None,
               instance_type=None, cloud_network=None, boot_disk_size=None, cancel=False,
               **prov_fill_kwargs):
        """Provisions an GCE instance with the given properties through CFME

        Args:
            email: Email of the requester
            first_name: Name of the requester
            last_name: Surname of the requester
            availability_zone: zone to deploy instance
            cloud_network: Name of the cloud network the instance should belong to
            instance_type: Type of the instance
            boot_disk_size: size of root disk
            cancel: Clicks the cancel button if `True`, otherwise clicks the submit button
                    (Defaults to `False`)
        Note:
            For more optional keyword arguments, see
            :py:data:`cfme.cloud.provisioning.provisioning_form`
        """
        from cfme.provisioning import provisioning_form
        # Nav to provision form and select image
        select_provision_image(template_name=self.template_name, provider=self.provider)

        fill(provisioning_form, dict(
            email=email,
            first_name=first_name,
            last_name=last_name,
            instance_name=self.name,
            availability_zone=availability_zone,
            instance_type=instance_type,
            cloud_network=cloud_network,
            boot_disk_size=boot_disk_size,
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
