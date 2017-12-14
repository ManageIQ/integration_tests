# -*- coding: utf-8 -*-
import attr
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToAttribute, NavigateToSibling

from wrapanapi.containers.service import Service as ApiService

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class ServiceAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Container Services"


class ServiceDetailsView(ContainerObjectDetailsBaseView):
    pass


@attr.s
class Service(BaseEntity, WidgetasticTaggable, Labelable):

    PLURAL = 'Container Services'
    all_view = ServiceAllView
    details_view = ServiceDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()

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


@attr.s
class ServiceCollection(BaseCollection):
    """Collection object for :py:class:`Service`."""

    ENTITY = Service


@navigator.register(ServiceCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ServiceAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Services')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Service, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = ServiceDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name).click()


@navigator.register(Service, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
