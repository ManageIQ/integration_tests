""" Page functions for Flavor pages
"""
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import Dropdown, Button, View

from cfme.base.ui import BaseLoggedInPage
from cfme.common import WidgetasticTaggable
from cfme.exceptions import FlavorNotFound
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from widgetastic_manageiq import (
    ItemsToolBarViewSelector, SummaryTable, Text, Table, PaginationPane, Accordion, ManageIQTree,
    Search, BreadCrumb)


class FlavorView(BaseLoggedInPage):
    @property
    def in_availability_zones(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Flavors']
        )


class FlavorToolBar(View):
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class FlavorEntities(View):
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='gtl_div']//table")
    search = View.nested(Search)


class FlavorDetailsToolBar(View):
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class FlavorDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class FlavorDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')


class FlavorAllView(FlavorView):
    @property
    def is_displayed(self):
        return (
            self.in_availability_zones and
            self.entities.title.text == 'Flavors')

    toolbar = FlavorToolBar()
    entities = FlavorEntities()
    paginator = PaginationPane()


class FlavorDetailsView(FlavorView):
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        expected_provider = self.context['object'].provider.name
        return (
            self.in_availability_zones and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title and
            self.entities.relationships.get_text_of('Cloud Provider') == expected_provider)

    toolbar = FlavorDetailsToolBar()
    sidebar = FlavorDetailsAccordion()
    entities = FlavorDetailsEntities()


class Flavor(WidgetasticTaggable, Navigatable):
    """
    Flavor class to support navigation
    """
    _param_name = "Flavor"

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)


@navigator.register(Flavor, 'All')
class FlavorAll(CFMENavigateStep):
    VIEW = FlavorAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Flavors')


@navigator.register(Flavor, 'Details')
class FlavorDetails(CFMENavigateStep):
    VIEW = FlavorDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=self.obj.name,
                cloud_provider=self.obj.provider.name)
        except NoSuchElementException:
            raise FlavorNotFound('Could not locate flavor "{}" on provider {}'
                                 .format(self.obj.name, self.obj.provider.name))
        row.click()
