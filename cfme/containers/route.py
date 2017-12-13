# -*- coding: utf-8 -*-
import attr
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToAttribute, NavigateToSibling
from wrapanapi.containers.route import Route as ApiRoute

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class RouteAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Routes"


class RouteDetailsView(ContainerObjectDetailsBaseView):
    pass


@attr.s
class Route(BaseEntity, WidgetasticTaggable, Labelable):

    PLURAL = 'Routes'
    all_view = RouteAllView
    details_view = RouteDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiRoute(self.provider.mgmt, self.name, self.project_name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        route_list = provider.mgmt.list_route()
        random.shuffle(route_list)
        return [cls(obj.name, obj.project_name, provider, appliance=appliance)
                for obj in itertools.islice(route_list, count)]


@attr.s
class RouteCollection(BaseCollection):
    """Collection object for :py:class:`Route`."""

    ENTITY = Route


@navigator.register(RouteCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = RouteAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Routes')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Route, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = RouteDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name).click()


@navigator.register(Route, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
