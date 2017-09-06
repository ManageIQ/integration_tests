from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator
from cfme.base.ui import BaseLoggedInPage
from widgetastic_manageiq import (Version, VersionPick, ItemsToolBarViewSelector, Table,
    FlashMessages, SummaryTable, BreadCrumb, Accordion, ManageIQTree, PaginationPane)
from widgetastic_patternfly import Button, Dropdown
from widgetastic.widget import View, NoSuchElementException, Text
from utils.log import logger


class SnapshotToolbar(View):
    policy = Dropdown('Policy')
    download = Dropdown('Download')  # title match
    view_selector = View.nested(ItemsToolBarViewSelector)


class SnapshotDetailsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button('Download summary in PDF format')


class SnapshotEntities(View):
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')


class SnapshotDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class SnapshotDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class SnapshotView(BaseLoggedInPage):
    """Base class for header and nav check"""
    @property
    def in_snapshot(self):
        nav = Snapshot.nav.pick(self.context['object'].appliance.version)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav
        )


class SnapshotAllView(SnapshotView):
    @property
    def is_displayed(self):
        return (
            self.in_snapshot and
            self.entities.title.text == 'Cloud Volume Snapshots')

    toolbar = View.nested(SnapshotToolbar)
    entities = View.nested(SnapshotEntities)
    paginator = View.nested(PaginationPane)


class SnapshotDetailsView(SnapshotView):
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        # The field in relationships table changes based on volume status so look for either
        try:
            provider = self.entities.relationships.get_text_of('Cloud Provider')
        except NameError:
            provider = self.entities.relationships.get_text_of('Parent Cloud Provider')
        return (
            self.in_snapshot and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title and
            provider == self.context['object'].provider.name)

    toolbar = View.nested(SnapshotDetailsToolbar)
    sidebar = View.nested(SnapshotDetailsAccordion)
    entities = View.nested(SnapshotDetailsEntities)


class Snapshot(Navigatable):
    nav = VersionPick({
        Version.lowest(): ['Storage', 'Block Storage', 'Volume Snapshots']})

    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        # TODO add storage provider parameter, needed for accurate details nav
        # the storage providers have different names then cloud providers
        # https://bugzilla.redhat.com/show_bug.cgi?id=1455270
        self.provider = provider


@navigator.register(Snapshot, 'All')
class SnapshotAll(CFMENavigateStep):
    VIEW = SnapshotAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        nav = Snapshot.nav.pick(self.obj.appliance.version)
        self.prerequisite_view.navigation.select(*nav)


@navigator.register(Snapshot, 'Details')
class SnapshotDetails(CFMENavigateStep):
    VIEW = SnapshotDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=self.obj.name, cloud_provider=self.obj.provider.name)
        except NoSuchElementException:
            logger.warn('Cannot identify snapshot by name and provider, looking by name only')
            try:
                row = self.prerequisite_view.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.table, name=self.obj.name)
            except NoSuchElementException:
                raise "Snapshot not found."
        row.click()
