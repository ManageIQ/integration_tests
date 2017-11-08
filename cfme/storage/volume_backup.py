# -*- coding: utf-8 -*-
import attr
import random

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import (
    Accordion,
    BaseEntitiesView,
    BreadCrumb,
    ItemsToolBarViewSelector,
    ManageIQTree,
    SummaryTable
)
from widgetastic_patternfly import BootstrapSelect, Button, Dropdown, FlashMessages
from widgetastic.widget import View, Text

from cfme.base.ui import BaseLoggedInPage
from cfme.common import TagPageView, WidgetasticTaggable
from cfme.exceptions import BackupNotFound, ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.wait import wait_for


class VolumeBackupToolbar(View):
    """The toolbar on the Volume Backup page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class VolumeBackupDetailsToolbar(View):
    """The toolbar on the Volume Backup detail page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button('Download summary in PDF format')


class VolumeBackupDetailsEntities(View):
    """The entities on the Volume Backup detail page"""
    breadcrumb = BreadCrumb()
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class VolumeBackupDetailSidebar(View):
    """The accordion on the Volume Backup details page"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class VolumeBackupView(BaseLoggedInPage):
    """A base view for all the Volume Backup pages"""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')
    flash = FlashMessages(
        './/div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
        'contains(@class, "flash_text_div")]')

    @property
    def in_volume_backup(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Storage', 'Block Storage', 'Volume Backups']
        )

    @property
    def is_displayed(self):
        return self.in_volume_backup


class VolumeBackupAllView(VolumeBackupView):
    """The all Volume Backup page"""
    toolbar = View.nested(VolumeBackupToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_volume_backup and
            self.title.text == 'Cloud Volume Backups')


class VolumeBackupDetailsView(VolumeBackupView):
    """The detail Volume Backup page"""
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)

        return (
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(VolumeBackupDetailsToolbar)
    sidebar = View.nested(VolumeBackupDetailSidebar)
    entities = View.nested(VolumeBackupDetailsEntities)


class VolumeRestoreView(VolumeBackupView):
    """The restore Volume backup view"""
    @property
    def is_displayed(self):
        return False

    volume_name = BootstrapSelect(name='volume_id')
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('cancel')


@attr.s
class VolumeBackup(BaseEntity, WidgetasticTaggable):
    """ Model of an Storage Volume Backups in cfme

    Args:
        name: name of the backup
        provider: provider
    """
    name = attr.ib()
    provider = attr.ib()

    def restore(self, name):
        """Restore the volume backup. this feature included in 5.9 and above.

        Args:
            name: volume name
        """
        view = navigate_to(self, 'Restore')
        view.volume_name.fill(name)
        view.save.click()
        view.flash.assert_success_message('Restoring Cloud Volume "{}"'.format(self.name))

    def refresh(self):
        self.provider.refresh_provider_relationships()
        self.browser.refresh()

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except BackupNotFound:
            return False

    @property
    def size(self):
        """ size of cloud volume backup.

        Returns:
            :py:class:`int' size of volume backup.
        """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Size')

    @property
    def status(self):
        """ Present status of cloud volume backup.

        Returns:
            :py:class:`str' status [available/restoring] of volume backup.
        """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Status')

    @property
    def volume(self):
        """ volume name of backup.

        Returns:
            :py:class:`str' respective volume name.
        """
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud Volume')


@attr.s
class VolumeBackupCollection(BaseCollection):
    """Collection object for :py:class:'cfme.storage.volume_backups.VolumeBackup' """
    ENTITY = VolumeBackup

    def all(self):
        """returning all backup objects for respective storage manager type"""
        view = navigate_to(self, 'All')

        backups = [self.instantiate(name=item['Name'], provider=self.filters.get('provider'))
                   for item in view.entities.elements.read()
                   if self.filters.get('provider').name in item['Cloud Provider']]
        return backups

    def delete(self, *backups):
        """Delete one or more backups

        Args:
            One or Multiple 'cfme.storage.volume_backup.VolumeBackup' objects
        """

        view = navigate_to(self, 'All')

        if view.entities.get_all():
            for backup in backups:
                try:
                    view.entities.get_entity(backup.name).check()
                except ItemNotFound:
                    raise BackupNotFound("Volume backup {} not found".format(backup.name))

            view.toolbar.configuration.item_select('Delete selected Backups', handle_alert=True)

            wait_for(
                lambda: not bool({backup.name for backup in backups} &
                             set(view.entities.all_entity_names)),
                message="Wait backups to disappear",
                delay=20,
                timeout=800,
                fail_func=random.choice(backups).refresh
            )

        else:
            raise BackupNotFound('No Volume Backups for Deletion')


@navigator.register(VolumeBackupCollection, 'All')
class All(CFMENavigateStep):
    VIEW = VolumeBackupAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
            self.prerequisite_view.navigation.select(
                'Storage', 'Block Storage', 'Volume Backups')


@navigator.register(VolumeBackup, 'Details')
class Details(CFMENavigateStep):
    VIEW = VolumeBackupDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(self.obj.name,
                                                       surf_pages=True).click()
        except ItemNotFound:
            raise BackupNotFound('Could not locate volume backup {}'.format(self.obj.name))


@navigator.register(VolumeBackup, 'EditTagsFromDetails')
class BackupDetailEditTag(CFMENavigateStep):
    """ This navigation destination help to WidgetasticTaggable"""
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(VolumeBackup, 'Restore')
class VolumeRestore(CFMENavigateStep):
    VIEW = VolumeRestoreView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Restore backup to Cloud Volume')
