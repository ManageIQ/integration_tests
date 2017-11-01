# -*- coding: utf-8 -*-

import attr
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic_manageiq import (
    Accordion, BaseEntitiesView, BreadCrumb, ItemsToolBarViewSelector, SummaryTable, Text,
    TimelinesView)
from widgetastic_patternfly import BootstrapNav, Button, Dropdown, FlashMessages
from widgetastic.widget import View
from wrapanapi.containers.node import Node as ApiNode

from cfme.base.login import BaseLoggedInPage
from cfme.common.vm_views import ManagePoliciesView
from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import ContainersProvider, Labelable
from cfme.exceptions import ItemNotFound, NodeNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to


class NodeToolbar(View):
    """The toolbar on the Node page"""
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class NodeDetailsToolbar(View):
    """The toolbar on the Node Details page"""
    monitoring = Dropdown('Monitoring')
    policy = Dropdown('Policy')
    # TODO: Add entry for the Web Console button
    download = Button(title='Download summary in PDF format')

    view_selector = View.nested(ItemsToolBarViewSelector)


class NodeDetailsAccordion(View):
    """The accordion on the Node Details page"""
    @View.nested
    class properties(Accordion):        # noqa
        nav = BootstrapNav('//div[@id="ems_prop"]//ul')

    @View.nested
    class relationships(Accordion):     # noqa
        nav = BootstrapNav('//div[@id="ems_rel"]//ul')


class NodeDetailsEntities(View):
    """The entities on the Node Details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    labels = SummaryTable(title='Labels')
    compliance = SummaryTable(title='Compliance')
    custom_attributes = SummaryTable(title='Custom Attributes')
    relationships = SummaryTable(title='Relationships')
    conditions = SummaryTable(title='Conditions')
    smart_management = SummaryTable(title='Smart Management')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class NodeView(BaseLoggedInPage):
    """A base view for all the Nodes pages"""
    TITLE_TEXT = "Nodes"

    @property
    def in_node(self):
        """Determine if the Nodes page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Containers', 'Container Nodes']
        )


class NodeAllView(NodeView):
    """The all Nodes page"""
    toolbar = View.nested(NodeToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return self.in_node and self.entities.title.text == 'Nodes'


@attr.s
class Node(BaseEntity, WidgetasticTaggable, Labelable):
    """Node Class"""
    PLURAL = 'Nodes'

    name = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        """API to use for Nodes"""
        return ApiNode(self.provider.mgmt, self.name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        node_list = provider.mgmt.list_node()
        random.shuffle(node_list)
        collection = NodeCollection(appliance)
        return [collection.instantiate(obj.name, provider)
                for obj in itertools.islice(node_list, count)]

    @property
    def exists(self):
        """Return True if the Node exists"""
        try:
            navigate_to(self, 'Details')
        except NoSuchElementException:
            return False
        else:
            return True


@attr.s
class NodeCollection(BaseCollection):
    """Collection object for :py:class:`cfme.containers.node.Node`"""

    ENTITY = Node

    def all(self):
        """Get all Nodes"""
        # container_nodes table has ems_id, join with ext_mgmgt_systems on id for provider name
        node_table = self.appliance.db.client['container_nodes']
        ems_table = self.appliance.db.client['ext_management_systems']
        node_query = self.appliance.db.client.session.query(node_table.name, ems_table.name)\
            .join(ems_table, node_table.ems_id == ems_table.id)
        nodes = []
        for name, provider_name in node_query.all():
            # Hopefully we can get by with just provider name?
            nodes.append(self.instantiate(name=name,
                                          provider=ContainersProvider(name=provider_name,
                                                                      appliance=self.appliance)))
        return nodes


# Still registering Node to keep on consistency on container objects navigations
# @navigator.register(Node, 'All')
@navigator.register(NodeCollection, 'All')
class NodeAll(CFMENavigateStep):
    VIEW = NodeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Navigate to the Nodes page"""
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Nodes')

    def resetter(self):
        """Reset the View"""
        self.view.entities.paginator.check_all()
        self.view.entities.paginator.uncheck_all()


class NodeDetailsView(NodeView):
    toolbar = View.nested(NodeDetailsToolbar)
    sidebar = View.nested(NodeDetailsAccordion)
    entities = View.nested(NodeDetailsEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_node and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title
        )


@navigator.register(Node, 'Details')
class NodeDetails(CFMENavigateStep):
    VIEW = NodeDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        """Navigate to the Node Details page"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True)
        except ItemNotFound:
            raise NodeNotFound('Failed to locate Node with name "{}"'.format(self.obj.name))
        row.click()

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(Node, 'EditTagsFromDetails')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        """Navigate to the Edit Tags page"""
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(Node, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    VIEW = ManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        """Navigate to the Manage Policies page"""
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


class NodeUtilizationView(NodeView):
    """View for utilization of a node"""
    title = Text('//div[@id="main-content"]//h1')

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return (
            self.in_node and
            self.title.text == '{} Capacity & Utilization'.format(self.context['object'].name)
        )


@navigator.register(Node, 'Utilization')
class Utilization(CFMENavigateStep):
    VIEW = NodeUtilizationView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        """Navigate to the Utilization page"""
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')


class NodeTimelinesView(TimelinesView, NodeView):
    """Timeline page for Nodes"""

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return (
            self.in_node and
            super(NodeTimelinesView, self).is_displayed
        )


@navigator.register(Node, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = NodeTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        """Navigate to the Timelines page"""
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')

# TODO Need Ad hoc Metrics
# TODO Need External Logging
