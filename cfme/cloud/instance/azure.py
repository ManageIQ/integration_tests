import attr
from riggerlib import recursive_update

from cfme.cloud.instance import Instance
from cfme.cloud.instance import InstanceCollection


@attr.s
class AzureInstance(Instance):
    # CFME & provider power control options Added by Jeff Teehan on 5-16-2016
    START = "Start"
    POWER_ON = START  # For compatibility with the infra objects.
    STOP = "Stop"
    POWER_OFF = STOP  # For compatibility with the infra objects.
    SUSPEND = "Suspend"
    DELETE = "Delete"
    TERMINATE = 'Delete'
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

    @property
    def vm_default_args(self):
        inst_args = super().vm_default_args
        provisioning = self.provider.data['provisioning']
        vm_user = provisioning.get('customize_username')
        vm_password = provisioning.get('customize_password')
        if self.appliance.version >= '5.10':
            instance_type = provisioning.get('instance_type').title()
        else:
            instance_type = provisioning.get('instance_type')
        recursive_update(inst_args, {
            'environment': {
                'public_ip_address': '<None>',
            },
            'customize': {
                'admin_username': vm_user,
                'root_password': vm_password
            },
            'properties': {
                'instance_type': instance_type}})
        return inst_args

    @property
    def vm_default_args_rest(self):
        inst_args = super().vm_default_args_rest
        provisioning = self.provider.data['provisioning']
        vm_user = provisioning.get('customize_username')
        vm_password = provisioning.get('customize_password')
        recursive_update(inst_args, {
            'vm_fields': {
                'root_username': vm_user,
                'root_password': vm_password}})
        return inst_args


@attr.s
class AzureInstanceCollection(InstanceCollection):
    ENTITY = AzureInstance
