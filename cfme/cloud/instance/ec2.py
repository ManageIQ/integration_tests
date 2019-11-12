import attr

from cfme.cloud.instance import Instance
from cfme.cloud.instance import InstanceCollection


@attr.s
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


@attr.s
class EC2InstanceCollection(InstanceCollection):
    # An instance of this would be an attribute of an EC2ProviderCollection
    ENTITY = EC2Instance
