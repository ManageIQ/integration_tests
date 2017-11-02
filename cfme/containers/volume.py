# -*- coding: utf-8 -*-
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from wrapanapi.containers.volume import Volume as ApiVolume

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView, click_row)
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from cfme.utils.appliance import Navigatable


class VolumeAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Persistent Volumes"


class VolumeDetailsView(ContainerObjectDetailsBaseView):
    SUMMARY_TEXT = "Persistent Volumes"


class Volume(WidgetasticTaggable, Navigatable):

    PLURAL = 'Volumes'
    all_view = VolumeAllView
    details_view = VolumeDetailsView

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

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


@navigator.register(Volume, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = VolumeAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Volumes')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(Volume, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = VolumeDetailsView

    def step(self):
        click_row(self.prerequisite_view, name=self.obj.name)


@navigator.register(Volume, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
