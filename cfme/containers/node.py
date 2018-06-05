# -*- coding: utf-8 -*-
# added new list_tbl definition
import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View
from widgetastic_manageiq import Button, Text, TimelinesView, BreadCrumb

from cfme.common import Taggable, TagPageView, PolicyProfileAssignable
from cfme.common.vm_console import ConsoleMixin
from cfme.containers.provider import (Labelable,
    ContainerObjectAllBaseView, LoggingableView, ContainerObjectDetailsBaseView,
    GetRandomInstancesMixin)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import (CFMENavigateStep, navigator,
                                                     navigate_to)
from cfme.common.provider_views import ProviderDetailsToolBar
from cfme.utils.providers import get_crud_by_name


class NodeDetailsToolBar(ProviderDetailsToolBar):
    web_console = Button('Web Console')


class NodeView(ContainerObjectAllBaseView, LoggingableView):
    """Container Nodes view"""

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
    """Container Nodes All view"""

    SUMMARY_TEXT = VersionPick({
        Version.lowest(): 'Nodes',
        '5.9': 'Container Nodes'
    })

    @property
    def is_displayed(self):
        return self.in_node and super(NodeAllView, self).is_displayed


class NodeDetailsView(ContainerObjectDetailsBaseView):
    """Container Nodes Detail view"""
    SUMMARY_TEXT = VersionPick({
        Version.lowest(): 'Nodes',
        '5.9': 'Container Nodes'
    })
    toolbar = View.nested(NodeDetailsToolBar)


@attr.s
class Node(BaseEntity, Taggable, Labelable, PolicyProfileAssignable, ConsoleMixin):
    """Node Class"""
    PLURAL = 'Nodes'
    all_view = NodeAllView
    details_view = NodeDetailsView

    name = attr.ib()
    provider = attr.ib()

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
class NodeCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Node`."""

    ENTITY = Node

    def all(self):
        # container_nodes table has ems_id, join with ext_mgmgt_systems on id for provider name
        # TODO Update to use REST API instead of DB queries
        node_table = self.appliance.db.client['container_nodes']
        ems_table = self.appliance.db.client['ext_management_systems']
        node_query = (
            self.appliance.db.client.session
                .query(node_table.name, ems_table.name)
                .join(ems_table, node_table.ems_id == ems_table.id))
        if self.filters.get('archived'):
            node_query = node_query.filter(node_table.deleted_on.isnot(None))
        if self.filters.get('active'):
            node_query = node_query.filter(node_table.deleted_on.is_(None))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            node_query = node_query.filter(ems_table.name == provider.name)
        nodes = []
        for name, ems_name in node_query.all():
            nodes.append(self.instantiate(name=name,
                                          provider=provider or get_crud_by_name(ems_name)))
        return nodes


@navigator.register(NodeCollection, 'All')
class All(CFMENavigateStep):
    VIEW = NodeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Nodes')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Node, 'Details')
class Details(CFMENavigateStep):
    VIEW = NodeDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   provider=self.obj.provider.name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(Node, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


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
    breadcrumb = BreadCrumb()

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return (
            self.in_node and
            '{} (Summary)'.format(self.context['object'].name) in self.breadcrumb.locations and
            self.is_timelines)


@navigator.register(Node, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = NodeTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        """Navigate to the Timelines page"""
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')

# TODO Need Ad hoc Metrics
# TODO Need External Logging
