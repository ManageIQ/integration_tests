# -*- coding: utf-8 -*-
import attr
from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from wrapanapi.containers.image_registry import ImageRegistry as ApiImageRegistry

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView,
                                      GetRandomInstancesMixin)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from cfme.utils.providers import get_crud_by_name


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


@attr.s
class ImageRegistryCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Image Registry`."""

    ENTITY = ImageRegistry

    def all(self):
        # container_image_registries table has ems_id,
        # join with ext_mgmgt_systems on id for provider name
        image_registry_table = self.appliance.db.client['container_image_registries']
        ems_table = self.appliance.db.client['ext_management_systems']
        image_registry_query = (
            self.appliance.db.client.session
                .query(image_registry_table.host, ems_table.name)
                .join(ems_table, image_registry_table.ems_id == ems_table.id))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            image_registry_query = image_registry_query.filter(ems_table.name == provider.name)
        image_registries = []
        for host, ems_name in image_registry_query.all():
            image_registries.append(
                self.instantiate(host=host,
                                 provider=provider or get_crud_by_name(ems_name)))

        return image_registries


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
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(host=self.obj.host).click()


@navigator.register(ImageRegistry, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
