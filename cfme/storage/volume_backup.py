import random

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import NoSuchElementException
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.base.ui import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common import TagPageView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


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
    download = Button('Print or export summary')


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
    search = View.nested(Search)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_volume_backup and
            self.title.text == 'Cloud Volume Backups')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class VolumeBackupDetailsView(VolumeBackupView):
    """The detail Volume Backup page"""
    @property
    def is_displayed(self):
        obj = self.context['object']

        return (
            self.in_volume_backup and
            self.title.text == obj.expected_details_title and
            self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb)

    toolbar = View.nested(VolumeBackupDetailsToolbar)
    sidebar = View.nested(VolumeBackupDetailSidebar)
    entities = View.nested(VolumeBackupDetailsEntities)


class VolumeRestoreEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeRestoreView(VolumeBackupView):
    """The restore Volume backup view"""
    @property
    def is_displayed(self):
        expected_title = 'Restore Cloud Volume Backup "{}"'.format(self.context['object'].name)
        return (self.entities.title.text == expected_title and
                self.entities.breadcrumb.active_location == expected_title)

    volume_name = BootstrapSelect(name='volume_id')
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('cancel')

    entities = View.nested(VolumeRestoreEntities)


@attr.s
class VolumeBackup(BaseEntity, Taggable):
    """ Model of an Storage Volume Backups in cfme

    Args:
        name: name of the backup
        provider: provider
    """
    name = attr.ib()
    provider = attr.ib()

    def restore(self, name):
        """Restore the volume backup.

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
    def size(self):
        """size of cloud volume backup.

        Returns:
            :py:class:`int` size of volume backup in GB.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.properties.get_text_of('Size').split()[0])

    @property
    def status(self):
        """Present status of cloud volume backup.

        Returns:
            :py:class:`str` status [available/restoring] of volume backup.
        """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Status')

    @property
    def volume(self):
        """volume name of backup.

        Returns:
            :py:class:`str` respective volume name.
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
        view.toolbar.view_selector.select("List View")
        backups = []

        try:
            if 'provider' in self.filters:
                for item in view.entities.elements.read():
                    if self.filters.get('provider').name in item['Storage Manager']:
                        backups.append(self.instantiate(name=item['Name'],
                                                        provider=self.filters.get('provider')))
            else:
                for item in view.entities.elements.read():
                    provider_name = item['Storage Manager'].split()[0]
                    provider = get_crud_by_name(provider_name)
                    backups.append(self.instantiate(name=item['Name'], provider=provider))
        except NoSuchElementException:
            if backups:
                # In the middle of reading, that may be bad
                logger.error(
                    'VolumeBackupCollection: NoSuchElementException in the middle of entities read')
                raise
            else:
                # This is probably fine, just warn
                logger.warning('The volume backup table is probably not present (=empty)')
        return backups

    def delete(self, *backups, **kwargs):
        """Delete one or more backups

        Args:
            One or Multiple 'cfme.storage.volume_backup.VolumeBackup' objects
        """

        view = navigate_to(self, 'All')

        if view.entities.get_all():
            for backup in backups:
                try:
                    view.entities.get_entity(name=backup.name).check()
                except ItemNotFound:
                    raise ItemNotFound("Volume backup {} not found".format(backup.name))

            view.toolbar.configuration.item_select('Delete selected Backups', handle_alert=True)

            if kwargs.get('wait', True):
                wait_for(
                    lambda: not bool({backup.name for backup in backups} &
                                     set(view.entities.all_entity_names)),
                    message="Wait backups to disappear",
                    delay=20,
                    timeout=800,
                    fail_func=random.choice(backups).refresh
                )

        else:
            raise ItemNotFound('No Volume Backups for Deletion')


@navigator.register(VolumeBackupCollection, 'All')
class All(CFMENavigateStep):
    VIEW = VolumeBackupAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Storage', 'Block Storage', 'Volume Backups')


@navigator.register(VolumeBackup, 'Details')
class Details(CFMENavigateStep):
    VIEW = VolumeBackupDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                       surf_pages=True).click()
        except ItemNotFound:
            raise ItemNotFound('Could not locate volume backup {}'.format(self.obj.name))


@navigator.register(VolumeBackup, 'EditTagsFromDetails')
class BackupDetailEditTag(CFMENavigateStep):
    """ This navigation destination help to Taggable"""
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
