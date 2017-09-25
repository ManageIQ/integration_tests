# -*- coding: utf-8 -*-
import random
import itertools
from cached_property import cached_property

from wrapanapi.containers.route import Route as ApiRoute

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView, click_row)
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from navmazing import NavigateToAttribute, NavigateToSibling
from cfme.utils.appliance import Navigatable


class RouteAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Routes"


class RouteDetailsView(ContainerObjectDetailsBaseView):
    pass


class Route(WidgetasticTaggable, Labelable, Navigatable):

    PLURAL = 'Routes'
    all_view = RouteAllView
    details_view = RouteDetailsView

    def __init__(self, name, project_name, provider, appliance=None):
        self.name = name
        self.project_name = project_name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

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


@navigator.register(Route, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = RouteAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Routes')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(Route, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = RouteDetailsView

    def step(self):
        click_row(self.prerequisite_view,
                  name=self.obj.name, project_name=self.obj.project_name)


@navigator.register(Route, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
