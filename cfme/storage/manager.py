# -*- coding: utf-8 -*-

from navmazing import NavigateToAttribute
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View, NoSuchElementException, Text
from widgetastic_manageiq import (
    Accordion,
    BootstrapSelect,
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
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.appliance import NavigatableMixin


class ManagerToolbar(View):
    """The toolbar on the Storage Manager or Provider page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')


class ManagerDetailsToolbar(View):
    """The toolbar on the Storage Manager or Provider detail page"""
    reload = Button(title='Reload Current Display')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    monitoring = Dropdown('Monitoring')
    download = Button(title='Download summary in PDF format')


class ManagerEntities(View):
    """The entities on the main list Storage Manager or Provider page"""
    table = Table(".//div[@id='list_grid']/table")


class ManagerDetailsEntities(View):
    """The entities on the Storage Manager or Provider details page"""
    breadcrumb = BreadCrumb()
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')
    status = SummaryTable('Status')


class ManagerDetailsAccordion(View):
    """The accordion on the Storage Manager or Provider details page"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class ManagerView(BaseLoggedInPage):
    """A base view for all the Storage Manager or Provider pages"""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    flash = FlashMessages(
        './/div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
        'contains(@class, "flash_text_div")]')

    @property
    def in_manager(self):
        nav = self.context['object'].nav.pick(self.context['object'].appliance.version)
        return(
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav)


class ManagerAllView(ManagerView):
    """The all Storage Manager or Provider page"""
    @property
    def is_displayed(self):
        return (
            self.in_manager and
            self.title.text in ('Storage Managers', self.context['object'].type))

    toolbar = View.nested(ManagerToolbar)
    entities = View.nested(ManagerEntities)
    paginator = PaginationPane()


class ManagerDetailsView(ManagerView):
    """The details page for Storage Manager or Provider"""
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)

        return(
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ManagerDetailsToolbar)
    sidebar = View.nested(ManagerDetailsAccordion)
    entities = View.nested(ManagerDetailsEntities)


class ManagerTagsView(ManagerView):
    """The tag page for Storage Manager or Provider"""
    breadcrumb = BreadCrumb()
    select_tag = BootstrapSelect('tag_cat')
    select_value = BootstrapSelect('tag_add')
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_manager and
            self.breadcrumb.active_location == 'Tag Assignment')


class ManagePoliciesView(ManagerView):
    """The policies page for Storage Manager or Provider"""
    breadcrumb = BreadCrumb()
    policies = BootstrapTreeview("protectbox")
    save_button = Button("Save")
    reset_button = Button("Reset")
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        return (
            self.in_manager and
            self.breadcrumb.active_location == "'Storage Manager' Policy Assignment")


class BlockManagerCollection(NavigatableMixin):
    """Collection object [block manager] for the :py:class:'cfme.storage.manager'"""

    def __init__(self, appliance):
        self.appliance = appliance
        self.nav = VersionPick({
            Version.lowest(): ['Storage', 'Storage Providers'],
            '5.8': ['Storage', 'Block Storage', 'Managers']})
        self.type = 'Block Storage Managers'

    def instantiate(self, name, provider):
        return Manager(name, provider, collection=self)


class ObjectManagerCollection(NavigatableMixin):
    """Collection object [object manager] for the :py:class:'cfme.storage.manager'"""

    def __init__(self, appliance):
        self.appliance = appliance
        self.nav = VersionPick({
            Version.lowest(): ['Storage', 'Storage Providers'],
            '5.8': ['Storage', 'Object Storage', 'Managers']})
        self.type = 'Object Storage Managers'

    def instantiate(self, name, provider):
        return Manager(name, provider, collection=self)


class Manager(NavigatableMixin):
    """ Model of an storage manager in cfme

    Args:
        name: Name of the object manager.
        provider: provider
        appliance: appliance
    """

    def __init__(self, name, provider, collection):
        self.name = name
        self.provider = provider
        self.collection = collection
        self.appliance = self.collection.appliance
        self.nav = self.collection.nav
        self.type = self.collection.type
        self.name_vari = VersionPick({Version.lowest(): 'Storage Provider',
                                  '5.8': 'Storage Manager'}).pick(self.appliance.version)

    def refresh(self, cancel=False):
        """Refresh storage manager"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Refresh Relationships and Power States',
                                               handle_alert=not cancel)

        if not cancel:
            msg = "Refresh Provider initiated for 1 {} from the CFME Database"\
                .format(self.name_vari)
            view.flash.assert_success_message(msg)

    def delete(self, wait=True):
        """Delete storage manager"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select(
            'Remove this {}'.format(self.name_vari), handle_alert=True)

        msg = "Delete initiated for 1 {} from the CFME Database".format(self.name_vari)
        view.flash.assert_success_message(msg)


@navigator.register(BlockManagerCollection, 'All')
@navigator.register(ObjectManagerCollection, 'All')
class ManagerAll(CFMENavigateStep):
    VIEW = ManagerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        nav = self.obj.nav.pick(self.obj.appliance.version)
        self.prerequisite_view.navigation.select(*nav)


@navigator.register(Manager, 'Details')
class ManagerDetails(CFMENavigateStep):
    VIEW = ManagerDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table, Name=self.obj.name)
            row.click()
        except NoSuchElementException:
            raise ItemNotFound('Could not locate {}'.format(self.obj.name))
