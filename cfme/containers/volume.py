# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import Taggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView,
                                      GetRandomInstancesMixin)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from cfme.utils.providers import get_crud_by_name


class VolumeAllView(ContainerObjectAllBaseView):
    """Container Volumes All view"""
    SUMMARY_TEXT = "Persistent Volumes"


class VolumeDetailsView(ContainerObjectDetailsBaseView):
    """Container Volumes Details view"""
    SUMMARY_TEXT = "Persistent Volumes"


@attr.s
class Volume(BaseEntity, Taggable, Labelable):

    PLURAL = 'Volumes'
    all_view = VolumeAllView
    details_view = VolumeDetailsView

    name = attr.ib()
    provider = attr.ib()


@attr.s
class VolumeCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Volume`."""

    ENTITY = Volume

    def all(self):
        # container_volumes table has ems_id, join with ext_mgmgt_systems on id for provider name
        volume_table = self.appliance.db.client['container_volumes']
        ems_table = self.appliance.db.client['ext_management_systems']
        volume_query = (
            self.appliance.db.client.session
                .query(volume_table.name, ems_table.name)
                .join(ems_table, volume_table.parent_id == ems_table.id)
                .filter(volume_table.type == 'PersistentVolume'))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            volume_query = volume_query.filter(ems_table.name == provider.name)
        volumes = []
        for name, ems_name in volume_query.all():
            volumes.append(self.instantiate(name=name,
                                            provider=provider or get_crud_by_name(ems_name)))

        return volumes


@navigator.register(VolumeCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = VolumeAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Volumes')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Volume, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = VolumeDetailsView

    def step(self):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(Volume, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
