# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import Accordion, ManageIQTree, View, Table
from widgetastic_patternfly import VerticalNavigation

from cfme.containers.provider import (ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView,
                                      GetRandomInstancesMixin, Labelable, LoggingableView)
from cfme.exceptions import ItemNotFound
from cfme.common import Taggable, TagPageView
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.providers import get_crud_by_name


class ContainerView(ContainerObjectAllBaseView, LoggingableView):
    """The base view for header and nav checking"""

    @property
    def in_containers(self):
        """Determine if the Containers page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Containers', 'Containers']
        )


class ContainerAllView(ContainerView):
    """Containers All view"""
    SUMMARY_TEXT = "Containers"
    containers = Table(locator="//div[@id='list_grid']//table")

    @View.nested
    class Filters(Accordion):  # noqa
        ACCORDION_NAME = "Filters"

        @View.nested
        class Navigation(VerticalNavigation):
            DIV_LINKS_MATCHING = './/div/ul/li/a[contains(text(), {txt})]'

            def __init__(self, parent, logger=None):
                VerticalNavigation.__init__(self, parent, '#Container_def_searches', logger=logger)

        tree = ManageIQTree()

    @property
    def is_displayed(self):
        return self.in_containers and super(ContainerAllView, self).is_displayed


class ContainerDetailsView(ContainerObjectDetailsBaseView):
    """Containers Detail view"""
    SUMMARY_TEXT = "Containers"


@attr.s
class Container(BaseEntity, Taggable, Labelable):
    """Container Class"""
    PLURAL = 'Containers'
    all_view = ContainerAllView
    details_view = ContainerDetailsView

    name = attr.ib()
    pod = attr.ib()
    provider = attr.ib()

    @property
    def project_name(self):
        return self.pod.project_name

    @property
    def exists(self):
        """Return True if the Container exists"""
        try:
            navigate_to(self, 'Details')
        except ItemNotFound:
            return False
        else:
            return True


@attr.s
class ContainerCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Container`."""

    ENTITY = Container

    def all(self):
        # containers table has ems_id, join with ext_mgmgt_systems on id for provider name
        # Then join with container_groups on the id for the pod
        # TODO Update to use REST API instead of DB queries
        container_table = self.appliance.db.client['containers']
        ems_table = self.appliance.db.client['ext_management_systems']
        pod_table = self.appliance.db.client['container_groups']
        container_pod_id = getattr(container_table, 'container_group_id', None)
        container_query = (
            self.appliance.db.client.session
                .query(container_table.name, pod_table.name, ems_table.name)
                .join(ems_table, container_table.ems_id == ems_table.id)
                .join(pod_table, container_pod_id == pod_table.id))
        if self.filters.get('archived'):
            container_query = container_query.filter(container_table.deleted_on.isnot(None))
        if self.filters.get('active'):
            container_query = container_query.filter(container_table.deleted_on.is_(None))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            container_query = container_query.filter(ems_table.name == provider.name)
        containers = []
        for name, pod_name, ems_name in container_query.all():
            containers.append(
                self.instantiate(name=name, pod=pod_name,
                                 provider=provider or get_crud_by_name(ems_name)))

        return containers


@navigator.register(ContainerCollection, 'All')
class ContainerAll(CFMENavigateStep):
    VIEW = ContainerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Containers')

    def resetter(self, *args, **kwargs):
        """Reset view and selection"""
        self.view.Filters.Navigation.select('ALL (Default)')
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Container, 'Details')
class ContainerDetails(CFMENavigateStep):
    VIEW = ContainerDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   pod_name=self.obj.pod,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(Container, 'EditTags')
class ContainerEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(Container, 'Timelines')
class ContainerTimeLines(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(Container, 'Utilization')
class ContainerUtilization(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')
