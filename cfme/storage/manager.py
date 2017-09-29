# -*- coding: utf-8 -*-

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View, NoSuchElementException, Text
from widgetastic_manageiq import (
    Accordion,
    BootstrapTreeview,
    BreadCrumb,
    ManageIQTree,
    PaginationPane,
    SummaryTable,
    Table
)
from widgetastic_patternfly import (
    Button,
    Dropdown,
    FlashMessages
)

from cfme.base.ui import BaseLoggedInPage
from cfme.common import TagPageView, WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.appliance import BaseCollection, BaseEntity


class StorageManagerToolbar(View):
    """The toolbar on the Storage Manager or Provider page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')


class StorageManagerDetailsToolbar(View):
    """The toolbar on the Storage Manager or Provider detail page"""
    reload = Button(title='Reload Current Display')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    monitoring = Dropdown('Monitoring')
    download = Button(title='Download summary in PDF format')


class StorageManagerEntities(View):
    """The entities on the main list Storage Manager or Provider page"""
    table = Table(".//div[@id='list_grid']/table")


class StorageManagerDetailsEntities(View):
    """The entities on the Storage Manager or Provider details page"""
    breadcrumb = BreadCrumb()
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')
    status = SummaryTable('Status')


class StorageManagerDetailsAccordion(View):
    """The accordion on the Storage Manager or Provider details page"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class StorageManagerView(BaseLoggedInPage):
    """A base view for all the Storage Manager or Provider pages"""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    flash = FlashMessages(
        './/div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
        'contains(@class, "flash_text_div")]')

    @property
    def in_manager(self):
        navigation_path = self.context['object'].navigation_path.pick(
            self.context['object'].appliance.version)
        return(
            self.logged_in_as_current_user and
            self.navigation.currently_selected == navigation_path)


class StorageManagerAllView(StorageManagerView):
    """The all Storage Manager or Provider page"""
    @property
    def is_displayed(self):
        return (
            self.in_manager and
            self.title.text in ('Storage Managers', self.context['object'].manager_type))

    toolbar = View.nested(StorageManagerToolbar)
    entities = View.nested(StorageManagerEntities)
    paginator = PaginationPane()


class StorageManagerDetailsView(StorageManagerView):
    """The details page for Storage Manager or Provider"""
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)

        return(
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(StorageManagerDetailsToolbar)
    sidebar = View.nested(StorageManagerDetailsAccordion)
    entities = View.nested(StorageManagerDetailsEntities)


class StorageManagePoliciesView(StorageManagerView):
    """The policies page for Storage Manager or Provider"""
    breadcrumb = BreadCrumb()
    policies = BootstrapTreeview("protectbox")
    save = Button("Save")
    reset = Button("Reset")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return (
            self.in_manager and
            self.breadcrumb.active_location == "'Storage Manager' Policy Assignment")


class BlockManagerCollection(BaseCollection):
    """Collection object [block manager] for the :py:class:'cfme.storage.manager'"""

    def __init__(self, appliance):
        self.appliance = appliance
        self.navigation_path = VersionPick({
            Version.lowest(): ['Storage', 'Storage Providers'],
            '5.8': ['Storage', 'Block Storage', 'Managers']})
        self.manager_type = 'Block Storage Managers'

    def instantiate(self, name, provider):
        return StorageManager(self, name, provider)


class ObjectManagerCollection(BaseCollection):
    """Collection object [object manager] for the :py:class:'cfme.storage.manager'"""

    def __init__(self, appliance):
        self.appliance = appliance
        self.navigation_path = VersionPick({
            Version.lowest(): ['Storage', 'Storage Providers'],
            '5.8': ['Storage', 'Object Storage', 'Managers']})
        self.manager_type = 'Object Storage Managers'

    def instantiate(self, name, provider):
        return StorageManager(self, name, provider)


class StorageManager(BaseEntity, WidgetasticTaggable):
    """ Model of an storage manager in cfme

    Args:
        collection: Instance of collection
        name: Name of the object manager.
        provider: Provider
    """

    def __init__(self, collection, name, provider):
        self.collection = collection
        self.appliance = self.collection.appliance
        self.name = name
        self.provider = provider
        self.navigation_path = self.collection.navigation_path
        self.manager_type = self.collection.manager_type
        self.storage_title = VersionPick({Version.lowest(): 'Storage Provider',
                                  '5.8': 'Storage Manager'}).pick(self.appliance.version)

    def refresh(self, cancel=False):
        """Refresh storage manager"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Refresh Relationships and Power States',
                                               handle_alert=not cancel)

        if not cancel:
            msg = "Refresh Provider initiated for 1 {} from the CFME Database".format(
                self.storage_title)
            view.flash.assert_success_message(msg)

    def delete(self, wait=True):
        """Delete storage manager"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select(
            'Remove this {}'.format(self.storage_title), handle_alert=True)

        msg = "Delete initiated for 1 {} from the CFME Database".format(self.storage_title)
        view.flash.assert_success_message(msg)


@navigator.register(BlockManagerCollection, 'All')
@navigator.register(ObjectManagerCollection, 'All')
class StorageManagerAll(CFMENavigateStep):
    VIEW = StorageManagerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        navigation_path = self.obj.navigation_path.pick(self.obj.appliance.version)
        self.prerequisite_view.navigation.select(*navigation_path)


@navigator.register(StorageManager, 'Details')
class StorageManagerDetails(CFMENavigateStep):
    VIEW = StorageManagerDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table, Name=self.obj.name)
            row.click()
        except NoSuchElementException:
            raise ItemNotFound('Could not locate {}'.format(self.obj.name))


@navigator.register(StorageManager, 'EditTagsFromDetails')
class StorageObjectDetailEditTag(CFMENavigateStep):
    """ This navigation destination help to WidgetasticTaggable"""
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
