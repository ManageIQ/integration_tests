# -*- coding: utf-8 -*-
import attr
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from wrapanapi.containers.volume import Volume as ApiVolume

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator


class VolumeAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Persistent Volumes"


class VolumeDetailsView(ContainerObjectDetailsBaseView):
    SUMMARY_TEXT = "Persistent Volumes"


@attr.s
class Volume(BaseEntity, WidgetasticTaggable, Labelable):

    PLURAL = 'Volumes'
    all_view = VolumeAllView
    details_view = VolumeDetailsView

    name = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiVolume(self.provider.mgmt, self.name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        volumes = provider.mgmt.list_volume()
        random.shuffle(volumes)
        return [cls(vol.name, provider, appliance=appliance)
                for vol in itertools.islice(volumes, count)]


@attr.s
class VolumeCollection(BaseCollection):
    """Collection object for :py:class:`Volume`."""

    ENTITY = Volume


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
        self.prerequisite_view.entities.get_entity(name=self.obj.name).click()


@navigator.register(Volume, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
