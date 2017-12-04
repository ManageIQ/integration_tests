# -*- coding: utf-8 -*-
import attr
import random
from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from wrapanapi.containers.image_registry import ImageRegistry as ApiImageRegistry

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (navigate_and_get_rows, ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator


class ImageRegistryAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Image Registries"


class ImageRegistryDetailsView(ContainerObjectDetailsBaseView):
    pass


@attr.s
class ImageRegistry(BaseEntity, WidgetasticTaggable, Navigatable):

    PLURAL = 'Image Registries'
    all_view = ImageRegistryAllView
    details_view = ImageRegistryDetailsView

    host = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiImageRegistry(self.provider.mgmt, self.name, self.host, None)

    @property
    def name(self):
        return self.host

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        ir_rows_list = navigate_and_get_rows(provider, cls, count, silent_failure=True)
        random.shuffle(ir_rows_list)
        return [cls(row.host.text, provider, appliance=appliance)
                for row in ir_rows_list]


@attr.s
class ImageRegistryCollection(BaseCollection):
    """Collection object for :py:class:`Image Registry`."""

    ENTITY = ImageRegistry


@navigator.register(ImageRegistryCollection, 'All')
class ImageRegistryAll(CFMENavigateStep):
    VIEW = ImageRegistryAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Image Registries')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(ImageRegistry, 'Details')
class ImageRegistryDetails(CFMENavigateStep):
    VIEW = ImageRegistryDetailsView
    prerequisite = NavigateToSibling('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(host=self.obj.host).click()


@navigator.register(ImageRegistry, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
