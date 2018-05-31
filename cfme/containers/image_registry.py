# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.utils import VersionPick, Version

from cfme.common import Taggable, TagPageView
from cfme.containers.provider import (ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView,
                                      GetRandomInstancesMixin)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from cfme.utils.providers import get_crud_by_name


class ImageRegistryAllView(ContainerObjectAllBaseView):
    """Container Images Registries All view"""
    SUMMARY_TEXT = VersionPick({
        Version.lowest(): 'Image Registries',
        '5.9': 'Container Image Registries'
    })


class ImageRegistryDetailsView(ContainerObjectDetailsBaseView):
    """Container Image Registries Detail view"""
    SUMMARY_TEXT = VersionPick({
        Version.lowest(): 'Image Registries',
        '5.9': 'Container Image Registries'
    })


@attr.s
class ImageRegistry(BaseEntity, Taggable, Navigatable):

    PLURAL = 'Image Registries'
    all_view = ImageRegistryAllView
    details_view = ImageRegistryDetailsView

    host = attr.ib()
    provider = attr.ib()

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
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(host=self.obj.host,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(ImageRegistry, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
