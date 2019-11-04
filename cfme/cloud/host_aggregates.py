""" Page functions for Host Aggregates pages
"""
import attr
from navmazing import NavigateToAttribute
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import View

from cfme.base.ui import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common import TaggableCollection
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.providers import get_crud_by_name
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Text


class HostAggregatesView(BaseLoggedInPage):
    @property
    def in_host_aggregates(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Host Aggregates']
        )


class HostAggregatesToolBar(View):
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    configuration = Dropdown('Configuration')
    view_selector = View.nested(ItemsToolBarViewSelector)


class HostAggregatesEntities(BaseEntitiesView):
    pass


class HostAggregatesDetailsToolBar(View):
    policy = Dropdown('Policy')
    download = Button(title='Print or export summary')
    configuration = Dropdown('Configuration')


class HostAggregatesDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class HostAggregatesDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')


class HostAggregatesAllView(HostAggregatesView):
    toolbar = HostAggregatesToolBar()
    paginator = PaginationPane()
    search = View.nested(Search)
    including_entities = View.include(HostAggregatesEntities, use_parent=True)

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()

    @property
    def is_displayed(self):
        return (
            self.in_host_aggregates and
            self.entities.title.text == 'Host Aggregates')


class HostAggregatesDetailsView(HostAggregatesView):
    @property
    def is_displayed(self):
        obj = self.context['object']
        return (
            self.in_host_aggregates and
            self.entities.title.text == obj.expected_details_title and
            self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb and
            self.entities.relationships.get_text_of('Cloud Provider') == obj.provider.name
        )

    toolbar = HostAggregatesDetailsToolBar()
    sidebar = HostAggregatesDetailsAccordion()
    entities = HostAggregatesDetailsEntities()


@attr.s
class HostAggregates(BaseEntity, Taggable):
    """
    Host Aggregates class to support navigation
    """
    _param_name = "HostAggregate"

    name = attr.ib()
    provider = attr.ib()
    ram = attr.ib(default=None)
    vcpus = attr.ib(default=None)
    disk = attr.ib(default=None)
    swap = attr.ib(default=None)
    rxtx = attr.ib(default=None)
    is_public = attr.ib(default=True)
    tenant = attr.ib(default=None)

    def refresh(self):
        """Refresh provider relationships and browser"""
        self.provider.refresh_provider_relationships()
        self.browser.refresh()

    @property
    def instance_count(self):
        """ number of instances using host aggregates.

        Returns:
            :py:class:`int` instance count.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.relationships.get_text_of('Instances'))


@attr.s
class HostAggregatesCollection(BaseCollection, TaggableCollection):
    ENTITY = HostAggregates

    def all(self):
        provider = self.filters.get('provider')  # None if no filter, need for entity instantiation
        view = navigate_to(self, 'All')
        result = []
        flavors = view.entities.get_all(surf_pages=True)
        for flavor in flavors:
            if provider is not None:
                if flavor.data['cloud_provider'] == provider.name:
                    entity = self.instantiate(flavor.data['name'], provider)
            else:
                entity = self.instantiate(flavor.data['name'],
                                          get_crud_by_name(flavor.data['cloud_provider']))
            result.append(entity)
        return result


@navigator.register(HostAggregatesCollection, 'All')
class HostAggregatesAll(CFMENavigateStep):
    VIEW = HostAggregatesAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Host Aggregates')


@navigator.register(HostAggregates, 'Details')
class HostAggregatesDetails(CFMENavigateStep):
    VIEW = HostAggregatesDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True)
        except ItemNotFound:
            raise ItemNotFound('Could not locate host aggregate "{}" on provider {}'
                               .format(self.obj.name, self.obj.provider.name))
        row.click()
