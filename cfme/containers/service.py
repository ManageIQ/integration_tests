# -*- coding: utf-8 -*-
import random
import itertools
from cached_property import cached_property

from wrapanapi.containers.service import Service as ApiService

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView, click_row)
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from navmazing import NavigateToAttribute, NavigateToSibling


class ServiceAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Container Services"


class ServiceDetailsView(ContainerObjectDetailsBaseView):
    pass


class Service(WidgetasticTaggable, Labelable, Navigatable):

    PLURAL = 'Container Services'
    all_view = ServiceAllView
    details_view = ServiceDetailsView

    def __init__(self, name, project_name, provider, appliance=None):
        self.name = name
        self.provider = provider
        self.project_name = project_name
        Navigatable.__init__(self, appliance=appliance)

    @cached_property
    def mgmt(self):
        return ApiService(self.provider.mgmt, self.name, self.project_name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        service_list = provider.mgmt.list_service()
        random.shuffle(service_list)
        return [cls(obj.name, obj.project_name, provider, appliance=appliance)
                for obj in itertools.islice(service_list, count)]


@navigator.register(Service, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ServiceAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Services')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(Service, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = ServiceDetailsView

    def step(self):
        click_row(self.prerequisite_view,
                  name=self.obj.name, project_name=self.obj.project_name)


@navigator.register(Service, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
