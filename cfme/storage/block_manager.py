from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator
from cfme.base.ui import BaseLoggedInPage
from widgetastic_manageiq import (Version, VersionPick, Table,
    FlashMessages, SummaryTable, BreadCrumb, Accordion, ManageIQTree, PaginationPane)
from widgetastic_patternfly import Button, Dropdown
from widgetastic.widget import View, NoSuchElementException, Text


class BlockManagerToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')


class BlockManagerDetailsToolbar(View):
    reload = Button(title='Reload Current Display')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    monitoring = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class BlockManagerEntities(View):
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')


class BlockManagerDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class BlockManagerDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class BlockManagerView(BaseLoggedInPage):
    """Base class for header and nav check"""
    @property
    def in_blockmanager(self):
        nav = BlockManager.nav.pick(self.context['object'].appliance.version)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav
        )


class BlockManagerAllView(BlockManagerView):
    @property
    def is_displayed(self):
        return (
            self.in_blockmanager and
            self.entities.title.text == 'Block Storage Managers')

    toolbar = View.nested(BlockManagerToolbar)
    entities = View.nested(BlockManagerEntities)
    paginator = View.nested(PaginationPane)


class BlockManagerDetailsView(BlockManagerView):
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        # The field in relationships table changes based on volume status so look for either
        try:
            provider = self.entities.relationships.get_text_of('Cloud Provider')
        except NameError:
            provider = self.entities.relationships.get_text_of('Parent Cloud Provider')
        return (
            self.in_blockmanager and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title and
            provider == self.context['object'].provider.name)

    toolbar = View.nested(BlockManagerDetailsToolbar)
    sidebar = View.nested(BlockManagerDetailsAccordion)
    entities = View.nested(BlockManagerDetailsEntities)


class BlockManager(Navigatable):
    # Navigation menu option
    nav = VersionPick({
        Version.lowest(): ['Storage', 'Block Storage', 'Managers']})

    def __init__(self, name, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name


@navigator.register(BlockManager, 'All')
class BlockManagerAll(CFMENavigateStep):
    VIEW = BlockManagerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        nav = BlockManager.nav.pick(self.obj.appliance.version)
        self.prerequisite_view.navigation.select(*nav)


@navigator.register(BlockManager, 'Details')
class BlockManagerDetails(CFMENavigateStep):
    VIEW = BlockManagerDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table, name=self.obj.name)
        except NoSuchElementException:
            raise "Block manager not found."
        row.click()
