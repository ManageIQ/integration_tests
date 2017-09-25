# -*- coding: utf-8 -*-
# added new list_tbl definition
import attr
import random
import itertools
from cached_property import cached_property

from wrapanapi.containers.node import Node as ApiNode

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import View
from widgetastic_manageiq import Button, Text, TimelinesView

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (ContainersProvider, Labelable,
    ContainerObjectAllBaseView, LoggingableView, ContainerObjectDetailsBaseView,
    click_row)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import (CFMENavigateStep, navigator,
                                                     navigate_to)
from cfme.utils.appliance import current_appliance
from cfme.common.provider_views import ProviderDetailsToolBar
from cfme.common.vm_views import ManagePoliciesView


class NodeDetailsToolBar(ProviderDetailsToolBar):
    web_console = Button('Web Console')


class NodeView(ContainerObjectAllBaseView, LoggingableView):
    SUMMARY_TEXT = "Nodes"

    @property
    def nodes(self):
        return self.table

    @property
    def in_node(self):
        """Determine if the Nodes page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Containers', 'Container Nodes']
        )


class NodeAllView(NodeView):
    @property
    def is_displayed(self):
        return self.in_node and super(NodeAllView, self).is_displayed


class NodeDetailsView(ContainerObjectDetailsBaseView):
    toolbar = View.nested(NodeDetailsToolBar)


@attr.s
class Node(BaseEntity, WidgetasticTaggable, Labelable):
    """Node Class"""
    PLURAL = 'Nodes'
    all_view = NodeAllView
    details_view = NodeDetailsView

    name = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        """API to use for Nodes"""
        return ApiNode(self.provider.mgmt, self.name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        appliance = appliance or current_appliance()
        node_list = provider.mgmt.list_node()
        random.shuffle(node_list)
        collection = NodeCollection(appliance)
        return [collection.instantiate(obj.name, provider)
                for obj in itertools.islice(node_list, count)]

    @property
    def exists(self):
        """Return True if the Node exists"""
        # TODO: move this to some ContainerObjectBase so it'll be shared among all objects
        try:
            navigate_to(self, 'Details')
        except NoSuchElementException:
            return False
        else:
            return True


@attr.s
class NodeCollection(BaseCollection):
    """Collection object for :py:class:`Node`."""

    ENTITY = Node

    def all(self):
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
@navigator.register(Node, 'All')
@navigator.register(NodeCollection, 'All')
class All(CFMENavigateStep):
    VIEW = NodeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Nodes')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(Node, 'Details')
class Details(CFMENavigateStep):
    VIEW = NodeDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        click_row(self.prerequisite_view,
                  name=self.obj.name, provider=self.obj.provider.name)


@navigator.register(Node, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(Node, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    VIEW = ManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        """Navigate to the Manage Policies page"""
        self.prerequisite_view.policy.item_select('Manage Policies')


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
        self.prerequisite_view.monitor.item_select('Utilization')


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
        self.prerequisite_view.monitor.item_select('Timelines')

# TODO Need Ad hoc Metrics
# TODO Need External Logging
