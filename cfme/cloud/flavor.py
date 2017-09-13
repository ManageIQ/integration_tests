""" Page functions for Flavor pages
"""
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import Dropdown, Button, View, BootstrapSelect
from cfme.base.ui import BaseLoggedInPage
from cfme.exceptions import FlavorNotFound
from cfme.web_ui import match_location, mixins
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from widgetastic_manageiq import (
    ItemsToolBarViewSelector, SummaryTable, Text, Table, PaginationPane, Accordion, ManageIQTree,
    Search, BreadCrumb, BaseNonInteractiveEntitiesView)


class FlavorView(BaseLoggedInPage):
    @property
    def in_availability_zones(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Flavors'] and
            match_location(controller='flavor', title='Flavors'))


class FlavorToolBar(View):
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class FlavorEntities(View):
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
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


class FlavorEditTagsView(FlavorView):
    @property
    def is_displayed(self):
        return (
            self.in_availability_zones and
            self.title.text == 'Tag Assignment' and
            '{} (Summary)'.format(self.context['object'].name) in self.breadcrumb.locations
        )

    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h3')
    category = BootstrapSelect("tag_cat")
    tag = BootstrapSelect("tag_add")
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class FlavorCollection(Navigatable):
    def instantiate(self, name, provider):
        return Flavor(name, provider, collection=self)

    def selection(self, *flavors):
        """Common method for flavors selection"""
        flavors = list(flavors)
        checked_flavors = []
        view = navigate_to(self, 'All')
        # double check we're in List View
        view.toolbar.view_selector.select('List View')
        if not view.entities.table.is_displayed:
            raise ValueError('No flavor found')
        for row in view.entities.table:
            for flavor in flavors:
                if flavor.name == row.name.text:
                    checked_flavors.append(flavor)
                    row[0].check()
                    break
            if set(flavors) == set(checked_flavors):
                break
        if set(flavors) != set(checked_flavors):
            missed_flavors = [f for f in flavors if f not in checked_flavors]
            raise ValueError('Some flavors were not found in the UI: {0}'.format(missed_flavors))
        view.toolbar.policy.item_select('Edit Tags')

    def add_tag(self, tag, *flavors):
        """Add given tag to flavor collections

        Args:
            tag: tuple describing tags
            flavors: list of :py:class:`cfme.cloud.flavor.Flavor` objects
        """
        self.selection(*flavors)
        mixins.add_tag(tag, navigate=False)

    def remove_tag(self, tag, *flavors):
        """Remove given tag from flavor collections

        Args:
            tag: tuple describing tags
            flavors: list of :py:class:`cfme.cloud.flavor.Flavor` objects
        """
        self.selection(*flavors)
        mixins.remove_tag(tag)


class Flavor(Navigatable):
    """Flavor class to support navigation"""

    def __init__(self, name, provider, collection=None):
        """Base class for flavor"""
        self.name = name
        self.provider = provider
        self.collection = collection or FlavorCollection()
        Navigatable.__init__(self, appliance=self.collection.appliance)

    def add_tag(self, tag, **kwargs):
        """Add given tag to flavor
        Args:
            tag: A :py:class:`cfme.cloud.flavor.Flavor` object describing tags
        """
        navigate_to(self, 'Details')
        mixins.add_tag(tag, **kwargs)

    def remove_tag(self, tag):
        """Remove given tag from flavor
        Args:
            tag: A :py:class:`cfme.cloud.flavor.Flavor` object describing tags
        """
        navigate_to(self, 'Details')
        mixins.remove_tag(tag)


@navigator.register(FlavorCollection, 'All')
class FlavorAll(CFMENavigateStep):
    VIEW = FlavorAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Flavors')


@navigator.register(Flavor, 'Details')
class FlavorDetails(CFMENavigateStep):
    VIEW = FlavorDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

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


@navigator.register(Flavor, 'EditTags')
class FlavorEditTags(CFMENavigateStep):
    VIEW = FlavorEditTagsView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
