# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View, Text, NoSuchElementException
from widgetastic_patternfly import Button, Dropdown, FlashMessages
from widgetastic_manageiq import (
    ItemsToolBarViewSelector, Search, Table, PaginationPane, BreadCrumb, SummaryTable, Accordion,
    ManageIQTree, TextInput, BootstrapSelect)

from cfme.base.ui import BaseLoggedInPage
from cfme.exceptions import VolumeNotFound
from cfme.web_ui import match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator
from utils.log import logger


class VolumeToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')  # title match
    view_selector = View.nested(ItemsToolBarViewSelector)


class VolumeDetailsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button('Download summary in PDF format')


class VolumeEntities(View):
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
    search = View.nested(Search)
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')


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
        nav = ['Storage', 'Volumes'] if self.context['object'].appliance.version < '5.8' else \
            ['Storage', 'Block Storage', 'Volumes']
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav and
            match_location(controller='cloud_volume', title='Cloud Volumes'))


class VolumeAllView(VolumeView):
    @property
    def is_displayed(self):
        return (
            self.in_volume and
            self.entities.title.text == 'Cloud Volumes')

    toolbar = View.nested(VolumeToolbar)
    entities = View.nested(VolumeEntities)
    paginator = View.nested(PaginationPane)


class VolumeDetailsView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title and
            self.entities.relationships.get_text_of('Parent Cloud Provider') == self.context[
                'object'].provider.name)

    toolbar = View.nested(VolumeDetailsToolbar)
    sidebar = View.nested(VolumeDetailsAccordion)
    entities = View.nested(VolumeDetailsEntities)


class VolumeAddEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeAddForm(View):
    volume_name = TextInput(name='name')
    size = TextInput(name='size')
    tenant = BootstrapSelect(id='cloud_tenant_id')
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


class Volume(Navigatable):
    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        # TODO add storage provider parameter, needed for accurate details nav
        # the storage providers have different names then cloud providers
        # https://bugzilla.redhat.com/show_bug.cgi?id=1455270
        self.provider = provider


@navigator.register(Volume, 'All')
class VolumeAll(CFMENavigateStep):
    VIEW = VolumeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        nav = ['Storage', 'Volumes'] if self.obj.appliance.version < '5.8' else \
            ['Storage', 'Block Storage', 'Volumes']
        self.prerequisite_view.navigation.select(*nav)


@navigator.register(Volume, 'Details')
class VolumeDetails(CFMENavigateStep):
    VIEW = VolumeDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=self.obj.name, cloud_provider=self.obj.provider.name)
        except NoSuchElementException:
            logger.warn('Cannot identify volume by name and provider, looking by name only')
            try:
                row = self.prerequisite_view.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.table, name=self.obj.name)
            except NoSuchElementException:
                raise VolumeNotFound
        row.click()


@navigator.register(Volume, 'Add')
class VolumeAdd(CFMENavigateStep):
    VIEW = VolumeAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Cloud Volume')
