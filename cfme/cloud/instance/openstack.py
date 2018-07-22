# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToSibling
from widgetastic.widget import View, NoSuchElementException
from widgetastic_patternfly import Button, BootstrapSelect
from widgetastic_manageiq import CheckboxSelect, Select, Input

from cfme.exceptions import OptionNotAvailable, DestinationNotFound
from cfme.common.vm_views import RightSizeView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from . import Instance, InstanceCollection, CloudInstanceView


@attr.s
class OpenStackInstance(Instance):
    # CFME & provider power control options
    START = "Start"  # START also covers RESUME and UNPAUSE (same as in CFME 5.4+ web UI)
    POWER_ON = START  # For compatibility with the infra objects.
    SUSPEND = "Suspend"
    DELETE = "Delete"
    TERMINATE = 'Delete'
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


@attr.s
class OpenstackInstanceCollection(InstanceCollection):
    ENTITY = OpenStackInstance


class AddFloatingIPView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        ip = Select(name='floating_ip')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        # Only the instance name is displayed, cannot confirm provider
        return False


class RemoveFloatingIPView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        ip = Select('floating_ip')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        # Only the instance name is displayed, cannot confirm provider
        return False


class AttachVolumeView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        volume = BootstrapSelect('volume_id')
        mountpoint = Input(name='device_path')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        # Only the instance name is displayed, cannot confirm provider
        return False


class DetachVolumeView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        volume = BootstrapSelect('volume_id')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        # Only the instance name is displayed, cannot confirm provider
        return False


class EvacuateView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        auto_select = CheckboxSelect('auto_select_host')
        shared_storage = CheckboxSelect('on_shared_storage')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        # Only the instance name is displayed, cannot confirm provider
        return False


class MigrateView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        auto_select = CheckboxSelect('auto_select_host')
        block_migration = CheckboxSelect('block_migration')
        disk_overcommit = CheckboxSelect('disk_over_commit')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        # Only the instance name is displayed, cannot confirm provider
        return False


class ReconfigureView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        flavor = BootstrapSelect('flavor')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        # Only the instance name is displayed, cannot confirm provider
        return False


@navigator.register(OpenStackInstance, 'AddFloatingIP')
class AddFloatingIP(CFMENavigateStep):
    VIEW = AddFloatingIPView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Associate a Floating IP with this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Add Floating IP option not available for instance')


@navigator.register(OpenStackInstance, 'RemoveFloatingIP')
class RemoveFloatingIP(CFMENavigateStep):
    VIEW = RemoveFloatingIPView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Disassociate a Floating IP from this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Remove Floating IP option not available for instance')


@navigator.register(OpenStackInstance, 'AttachVolume')
class AttachVolume(CFMENavigateStep):
    VIEW = AttachVolumeView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Attach a Cloud Volume to this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Attach Cloud Volume option not available for instance')


@navigator.register(OpenStackInstance, 'DetachVolume')
class DetachVolume(CFMENavigateStep):
    VIEW = DetachVolumeView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Detach a Cloud Volume from this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Detach Cloud Volume option not available for instance')


@navigator.register(OpenStackInstance, 'Evacuate')
class Evacuate(CFMENavigateStep):
    VIEW = EvacuateView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        lifecycle = self.prerequisite_view.toolbar.lifecycle
        try:
            lifecycle.item_select('Evacuate Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Evacuate option not available for instance')


@navigator.register(OpenStackInstance, 'Migrate')
class Migrate(CFMENavigateStep):
    VIEW = MigrateView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        lifecycle = self.prerequisite_view.toolbar.lifecycle
        try:
            lifecycle.item_select('Migrate Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Migrate option not available for instance')


@navigator.register(OpenStackInstance, 'Reconfigure')
class Reconfigure(CFMENavigateStep):
    VIEW = ReconfigureView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Reconfigure this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Reconfigure option not available for instance')


@navigator.register(OpenStackInstance, 'RightSize')
class RightSize(CFMENavigateStep):
    VIEW = RightSizeView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Right-Size Recommendations')
        except NoSuchElementException:
            raise DestinationNotFound('Right Size option not available for instance')
