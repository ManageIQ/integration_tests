import attr
from navmazing import NavigateToSibling
from riggerlib import recursive_update
from widgetastic.utils import partial_match
from widgetastic.widget import NoSuchElementException
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button

from cfme.cloud.instance import CloudInstanceView
from cfme.cloud.instance import Instance
from cfme.cloud.instance import InstanceCollection
from cfme.exceptions import DestinationNotFound
from cfme.exceptions import displayed_not_implemented
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for
from widgetastic_manageiq import CheckboxSelect
from widgetastic_manageiq import Input
from widgetastic_manageiq import Select


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

    def attach_volume(self, name, mountpoint=None):
        view = navigate_to(self, 'AttachVolume')
        view.form.fill({
            'volume': name,
            'mountpoint': mountpoint
        })
        view.form.submit_button.click()

    def detach_volume(self, name):
        view = navigate_to(self, 'DetachVolume')
        view.fill({'volume': name})

    def reconfigure(self, flavor):
        view = navigate_to(self, 'Reconfigure')
        view.form.flavor.fill(partial_match(flavor))
        view.form.submit_button.click()
        view.flash.assert_no_error()

    @property
    def volume_count(self):
        """ number of attached volumes to instance.

        Returns:
            :py:class:`int` volume count.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.summary('Relationships').get_text_of('Cloud Volumes'))

    @property
    def vm_default_args(self):
        inst_args = super(OpenStackInstance, self).vm_default_args
        provisioning = self.provider.data['provisioning']
        recursive_update(inst_args, {
            'environment': {
                'cloud_tenant': provisioning.get('cloud_tenant'),
            }})
        return inst_args


@attr.s
class OpenstackInstanceCollection(InstanceCollection):
    ENTITY = OpenStackInstance


class AddFloatingIPView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        ip = Select(name='floating_ip')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    # Only the instance name is displayed, cannot confirm provider
    is_displayed = displayed_not_implemented


class RemoveFloatingIPView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        ip = Select('floating_ip')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    # Only the instance name is displayed, cannot confirm provider
    is_displayed = displayed_not_implemented


class AttachVolumeView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        volume = BootstrapSelect('volume_id')
        mountpoint = Input(name='device_path')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    # Only the instance name is displayed, cannot confirm provider
    is_displayed = displayed_not_implemented


class DetachVolumeView(CloudInstanceView):
    volume = BootstrapSelect('volume_id')
    submit_button = Button('Submit')
    cancel_button = Button('Cancel')

    # Only the instance name is displayed, cannot confirm provider
    is_displayed = displayed_not_implemented

    def after_fill(self, was_change):
        # TODO: Remove this method once BZ1647695 has been fixed
        self.submit_button.click()
        if was_change and BZ(1647695, forced_streams=['5.10', 'upstream']).blocks:
            instance = self.context['object']
            view = self.browser.create_view(navigator.get_class(instance, 'Details').VIEW)
            wait_for(lambda: view.entities.title.text == 'Instance "{}"'.format(
                self.context['object'].name), timeout=20, delay=2)


class EvacuateView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        auto_select = CheckboxSelect('auto_select_host')
        shared_storage = CheckboxSelect('on_shared_storage')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    # Only the instance name is displayed, cannot confirm provider
    is_displayed = displayed_not_implemented


class MigrateView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        auto_select = CheckboxSelect('auto_select_host')
        block_migration = CheckboxSelect('block_migration')
        disk_overcommit = CheckboxSelect('disk_over_commit')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    # Only the instance name is displayed, cannot confirm provider
    is_displayed = displayed_not_implemented


class ReconfigureView(CloudInstanceView):
    @View.nested
    class form(View):  # noqa
        flavor = Select(name='flavor_id')
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    # Only the instance name is displayed, cannot confirm provider
    is_displayed = displayed_not_implemented


@navigator.register(OpenStackInstance, 'AddFloatingIP')
class AddFloatingIP(CFMENavigateStep):
    VIEW = AddFloatingIPView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Associate a Floating IP with this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Add Floating IP option not available for instance')


@navigator.register(OpenStackInstance, 'RemoveFloatingIP')
class RemoveFloatingIP(CFMENavigateStep):
    VIEW = RemoveFloatingIPView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Disassociate a Floating IP from this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Remove Floating IP option not available for instance')


@navigator.register(OpenStackInstance, 'AttachVolume')
class AttachVolume(CFMENavigateStep):
    VIEW = AttachVolumeView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Attach a Cloud Volume to this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Attach Cloud Volume option not available for instance')


@navigator.register(OpenStackInstance, 'DetachVolume')
class DetachVolume(CFMENavigateStep):
    VIEW = DetachVolumeView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Detach a Cloud Volume from this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Detach Cloud Volume option not available for instance')


@navigator.register(OpenStackInstance, 'Evacuate')
class Evacuate(CFMENavigateStep):
    VIEW = EvacuateView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        lifecycle = self.prerequisite_view.toolbar.lifecycle
        try:
            lifecycle.item_select('Evacuate Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Evacuate option not available for instance')


@navigator.register(OpenStackInstance, 'Migrate')
class Migrate(CFMENavigateStep):
    VIEW = MigrateView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        lifecycle = self.prerequisite_view.toolbar.lifecycle
        try:
            lifecycle.item_select('Migrate Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Migrate option not available for instance')


@navigator.register(OpenStackInstance, 'Reconfigure')
class Reconfigure(CFMENavigateStep):
    VIEW = ReconfigureView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        configuration = self.prerequisite_view.toolbar.configuration
        try:
            configuration.item_select('Reconfigure this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Reconfigure option not available for instance')
