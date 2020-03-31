import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import NoSuchElementException
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.base.ui import BaseLoggedInPage
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.common import TaggableCollection
from cfme.common import TagPageView
from cfme.exceptions import displayed_not_implemented
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.providers import get_crud_by_name
from cfme.utils.update import Updateable
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import BootstrapSelect
from widgetastic_manageiq import BootstrapSwitch
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


class VolumeToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')  # title match
    view_selector = View.nested(ItemsToolBarViewSelector)


class VolumeDetailsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button('Print or export summary')


class VolumeDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class VolumeDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class VolumeView(BaseLoggedInPage):
    """Base class for header and nav check"""

    @property
    def in_volume(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Storage', 'Block Storage', 'Volumes'])


class VolumeAllView(VolumeView):
    toolbar = View.nested(VolumeToolbar)
    search = View.nested(Search)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_volume and
            self.entities.title.text == 'Cloud Volumes'
        )

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class StorageManagerVolumeAllView(VolumeAllView):
    @property
    def is_displayed(self):
        return (
            self.entities.title.text == "{} (All Cloud Volumes)".format(self.context['object'].name)
        )


class VolumeDetailsView(VolumeView):
    @property
    def is_displayed(self):
        obj = self.context['object']
        # The field in relationships table changes based on volume status so look for either
        try:
            provider = self.entities.relationships.get_text_of('Cloud Provider')
        except NameError:
            provider = self.entities.relationships.get_text_of('Parent Cloud Provider')
        return (self.in_volume and
                self.entities.title.text == obj.expected_details_title and
                self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb and
                provider == self.context['object'].provider.name)

    toolbar = View.nested(VolumeDetailsToolbar)
    sidebar = View.nested(VolumeDetailsAccordion)
    entities = View.nested(VolumeDetailsEntities)


class VolumeAddEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeAddForm(View):
    storage_manager = BootstrapSelect(name='storage_manager_id')
    tenant = BootstrapSelect(name='cloud_tenant_id')  # is for openstack block storage only
    volume_name = TextInput(name='name')
    volume_type = BootstrapSelect(name=VersionPicker({Version.lowest(): 'aws_volume_type',
                                                      '5.10': 'volume_type'}))
    volume_size = TextInput(name='size')
    # az is for ec2 block storage only
    az = BootstrapSelect(
        name=VersionPicker(
            {Version.lowest(): 'aws_availability_zone_id', '5.11': 'availability_zone_id'}))
    iops = TextInput(name='aws_iops')  # is for ec2 block storage only
    encryption = BootstrapSwitch(name="aws_encryption")  # is for ec2 block storage only
    add = Button('Add')
    cancel = Button('Cancel')


class VolumeAddView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = "Add New Cloud Volume"
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    entities = View.nested(VolumeAddEntities)
    form = View.nested(VolumeAddForm)


class VolumeEditView(VolumeView):
    is_displayed = displayed_not_implemented

    volume_name = TextInput(name='name')
    volume_size = TextInput(name='size')
    save = Button('Save')


class VolumeBackupEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeBackupView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = 'Create Backup for Cloud Volume "{}"'.format(self.context['object'].name)
        return (
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    backup_name = TextInput(name='backup_name')
    # options
    incremental = BootstrapSwitch(name='incremental')
    force = BootstrapSwitch(name='force')

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    entities = View.nested(VolumeBackupEntities)


class VolumeSnapshotView(VolumeView):
    is_displayed = displayed_not_implemented

    snapshot_name = TextInput(name='snapshot_name')

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class VolumeAttachInstanceEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class AttachInstanceView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = 'Attach Cloud Volume "{name}"'.format(name=self.context['object'].name)
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title
        )

    instance = BootstrapSelect('vm_id')
    mountpoint = Input(name='device_path')
    attach = Button('Attach')
    cancel = Button('Cancel')
    reset = Button('Reset')

    entities = View.nested(VolumeAttachInstanceEntities)


class VolumeDetachInstanceEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class DetachInstanceView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = 'Detach Cloud Volume "{name}"'.format(name=self.context['object'].name)
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title
        )

    instance = BootstrapSelect(name='vm_id')
    detach = Button('Detach')
    cancel = Button('Cancel')

    entities = View.nested(VolumeDetachInstanceEntities)


@attr.s
class Volume(BaseEntity, CustomButtonEventsMixin, Updateable, Taggable):
    name = attr.ib()
    provider = attr.ib()

    def wait_for_disappear(self, timeout=300):
        """Wait for disappear the volume"""
        try:
            wait_for(lambda: not self.exists,
                     timeout=timeout,
                     message='Wait for cloud Volume to disappear',
                     delay=20,
                     fail_func=self.refresh)
        except TimedOutError:
            logger.error('Timed out waiting for Volume to disappear, continuing')

    def update(self, updates, from_manager=None):
        """Edit cloud volume"""
        if from_manager:
            view = navigate_to(self.parent.manager, 'Volumes')
            view.entities.get_entity(surf_pages=True, name=self.name).ensure_checked()
            view.toolbar.configuration.item_select('Edit selected Cloud Volume')
            view = view.browser.create_view(VolumeEditView, additional_context={'object': self})
        else:
            view = navigate_to(self, 'Edit')
        view.fill(updates)

        view.save.click()
        view.flash.assert_success_message('Cloud Volume "{}" updated'.format(
            updates.get('volume_name')))
        wait_for(lambda: not self.exists, delay=20, timeout=500, fail_func=self.refresh)
        volume_collection = self.appliance.collections.volumes
        return volume_collection.instantiate(
            name=updates.get('volume_name'), provider=self.provider)

    def delete(self, wait=True, from_manager=None):
        """Delete the Volume"""
        if from_manager:
            view = navigate_to(self.parent.manager, 'Volumes')
            view.entities.get_entity(surf_pages=True, name=self.name).ensure_checked()
            view.toolbar.configuration.item_select(
                'Delete selected Cloud Volumes', handle_alert=True)
        else:
            view = navigate_to(self, 'Details')
            view.toolbar.configuration.item_select('Delete this Cloud Volume', handle_alert=True)
        view.flash.assert_success_message('Delete initiated for 1 Cloud Volume.')

        if wait:
            self.wait_for_disappear(500)

    def refresh(self):
        """Refresh provider relationships and browser"""
        self.provider.refresh_provider_relationships()
        self.browser.refresh()

    def create_backup(self, name, incremental=None, force=None):
        """create backup of cloud volume"""
        initial_backup_count = self.backups_count
        view = navigate_to(self, 'Backup')
        view.backup_name.fill(name)
        view.incremental.fill(incremental)
        view.force.fill(force)

        view.save.click()
        view.flash.assert_success_message(f'Backup for Cloud Volume "{self.name}" created')

        wait_for(lambda: self.backups_count > initial_backup_count,
                 delay=20,
                 timeout=1000,
                 fail_func=self.refresh)

    def create_snapshot(self, name, cancel=False, reset=False, from_manager=False):
        """create snapshot of cloud volume"""
        snapshot_collection = self.appliance.collections.volume_snapshots
        if from_manager:
            view = navigate_to(self.parent.manager, 'Volumes')
            view.entities.get_entity(surf_pages=True, name=self.name).ensure_checked()
            view.toolbar.configuration.item_select('Create a Snapshot of selected Cloud Volume')
            view = view.browser.create_view(VolumeSnapshotView, additional_context={'object': self})
        else:
            view = navigate_to(self, 'Snapshot')

        changed = view.snapshot_name.fill(name)

        # For changes only Save and Reset button activate
        if changed:
            if reset:
                view.reset.click()
                return None

            elif cancel:
                view.cancel.click()
                return None

            else:
                view.save.click()
                return snapshot_collection.instantiate(name, self.provider)

    def attach_instance(self, name, mountpoint=None, cancel=False, reset=False,
                        from_manager=None):
        if from_manager:
            view = navigate_to(self.parent.manager, 'Volumes')
            view.entities.get_entity(surf_pages=True, name=self.name).ensure_checked()
            view.toolbar.configuration.item_select('Attach selected Cloud Volume to an Instance')
            view = view.browser.create_view(AttachInstanceView, additional_context={'object': self})
        else:
            view = navigate_to(self, 'AttachInstance')

        # Reset and Attach buttons are only active when view is changed
        changed = view.fill({'instance': name, 'mountpoint': mountpoint})

        if cancel or not changed:
            if not changed:
                logger.info("attach_instance: the form was unchanged")
            self.click.cancel()

        elif changed:
            if reset:
                view.reset.click()
            else:
                view.attach.click()
                view = self.create_view(VolumeDetailsView)
                view.flash.assert_no_error()

    def detach_instance(self, name, cancel=False, from_manager=None):
        if from_manager:
            view = navigate_to(self.parent.manager, 'Volumes')
            view.entities.get_entity(surf_pages=True, name=self.name).ensure_checked()
            view.toolbar.configuration.item_select('Detach selected Cloud Volume from an Instance')
            view = view.browser.create_view(DetachInstanceView, additional_context={'object': self})
        else:
            view = navigate_to(self, 'DetachInstance')

        # Detach button is only active when view is changed
        changed = view.instance.fill(name)

        if cancel or not changed:
            if not changed:
                logger.info("detach_instance: the form was unchanged")
            self.click.cancel()
        elif changed:
            view.detach.click()
            view = self.create_view(VolumeDetailsView)
            view.flash.assert_no_error()

    @property
    def status(self):
        """ status of cloud volume.
        Returns:
            :py:class:`str` Status of volume.
        """
        view = navigate_to(self.parent, 'All')
        view.toolbar.view_selector.select("List View")
        if self.provider.one_of(OpenStackProvider):
            self.refresh()
        else:
            view.browser.refresh()
        try:
            ent = view.entities.get_entity(name=self.name, surf_pages=True)
            return ent.data["status"]
        except ItemNotFound:
            return False

    @property
    def size(self):
        """ size of storage cloud volume.

        Returns:
            :py:class:`str` size of volume.
        """
        view = navigate_to(self, 'Details')
        view.browser.refresh()
        return view.entities.properties.get_text_of('Size')

    @property
    def tenant(self):
        """ cloud tenants for volume.

        Returns:
            :py:class:`str` respective tenants.
        """
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud Tenants')

    @property
    def backups_count(self):
        """ number of available backups for volume.

        Returns:
            :py:class:`int` backup count.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.relationships.get_text_of('Cloud Volume Backups'))

    @property
    def snapshots_count(self):
        """ number of available snapshots for volume.

        Returns:
            :py:class:`int` snapshot count.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.relationships.get_text_of('Cloud Volume Snapshots'))

    @property
    def instance_count(self):
        """ number of instances attached to volume.

        Returns:
            :py:class:`int` instance count.
        """
        view = navigate_to(self, 'Details', force=True)
        return int(view.entities.relationships.get_text_of('Instances'))


@attr.s
class VolumeCollection(BaseCollection, TaggableCollection):
    """Collection object for the :py:class:'cfme.storage.volume.Volume'. """
    ENTITY = Volume

    @property
    def manager(self):
        coll = self.appliance.collections.block_managers.filter({"provider": self.filters.get(
            'provider')})
        return coll.all()[0]

    def create(self, name, provider, tenant=None, volume_type=None, volume_size=1,
               cancel=False, az=None, from_manager=False):
        """Create new storage volume

        Args:
            name: volume name
            from_manager: create on the storage manager
            tenant: tenant name
            volume_size: volume size in GB
            provider: provider
            cancel: bool

        Returns:
            object for the :py:class: cfme.storage.volume.Volume
        """
        if from_manager:
            view = navigate_to(self.manager, 'AddVolume')
        else:
            view = navigate_to(self, 'Add')

        if not cancel:
            view.form.fill({'storage_manager': self.manager.name,
                            'tenant': tenant,
                            'volume_name': name,
                            'volume_type': volume_type,
                            'volume_size': volume_size,
                            'az': az,
                            })
            view.form.add.click()
            base_message = 'Cloud Volume "{}" created'
            view.flash.assert_success_message(base_message.format(name))

            volume = self.instantiate(name, provider)
            wait_for(lambda: volume.exists, delay=50, timeout=1500, fail_func=volume.refresh)
            return volume
        else:
            view.form.cancel.click()

    def delete(self, *volumes):
        """Delete one or more Volumes from list of Volumes

        Args:
            One or Multiple 'cfme.storage.volume.Volume' objects
        """

        view = navigate_to(self, 'All')

        if view.entities.get_all():
            for volume in volumes:
                try:
                    view.entities.get_entity(name=volume.name).ensure_checked()
                except ItemNotFound:
                    raise ItemNotFound(f"Volume {volume.name} not found")

            view.toolbar.configuration.item_select('Delete selected Cloud Volumes',
                                                   handle_alert=True)

            for volume in volumes:
                volume.wait_for_disappear()
        else:
            raise ItemNotFound('No Cloud Volume for Deletion')

    def all(self, from_manager=None):
        """returning all Volumes objects for respective storage manager type"""
        if from_manager:
            view = navigate_to(self.manager, 'Volumes')
        else:
            view = navigate_to(self, 'All')
        view.toolbar.view_selector.select("List View")
        volumes = []
        try:
            if 'provider' in self.filters:
                for item in view.entities.elements.read():
                    if self.filters.get('provider').name in item['Storage Manager']:
                        volumes.append(self.instantiate(name=item['Name'],
                                                        provider=self.filters.get('provider')))
            else:
                for item in view.entities.elements.read():
                    provider_name = item['Storage Manager'].split()[0]
                    provider = get_crud_by_name(provider_name)
                    volumes.append(self.instantiate(name=item['Name'], provider=provider))

        except NoSuchElementException:
            if volumes:
                logger.error('VolumeCollection: '
                             'NoSuchElementException in the middle of entities read')
            else:
                logger.warning('The volumes table is probably not present or empty')
        return volumes


@navigator.register(VolumeCollection, 'All')
class VolumeAll(CFMENavigateStep):
    VIEW = VolumeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Storage', 'Block Storage', 'Volumes')


@navigator.register(Volume, 'Details')
class VolumeDetails(CFMENavigateStep):
    VIEW = VolumeDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):

        try:
            self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                       surf_pages=True).click()

        except ItemNotFound:
            raise ItemNotFound(f'Volume {self.obj.name} not found')


@navigator.register(VolumeCollection, 'Add')
class VolumeAdd(CFMENavigateStep):
    VIEW = VolumeAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Cloud Volume')


@navigator.register(Volume, 'Edit')
class VolumeEdit(CFMENavigateStep):
    VIEW = VolumeEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Cloud Volume')


@navigator.register(Volume, 'Backup')
class VolumeBackup(CFMENavigateStep):
    VIEW = VolumeBackupView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Create a Backup of this Cloud '
                                                                 'Volume')


@navigator.register(Volume, 'Snapshot')
class VolumeSnapshot(CFMENavigateStep):
    VIEW = VolumeSnapshotView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Create a Snapshot of this Cloud '
                                                                 'Volume')


@navigator.register(Volume, 'EditTagsFromDetails')
class VolumeDetailEditTag(CFMENavigateStep):
    """ This navigation destination help to Taggable"""
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(Volume, 'AttachInstance')
class AttachInstance(CFMENavigateStep):
    VIEW = AttachInstanceView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Attach this Cloud Volume to an '
                                                                 'Instance')


@navigator.register(Volume, 'DetachInstance')
class DetachInstance(CFMENavigateStep):
    VIEW = DetachInstanceView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Detach this Cloud Volume from an '
                                                                 'Instance')
