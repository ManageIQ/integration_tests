# -*- coding: utf-8 -*-
import random
from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from wrapanapi.containers.image_registry import ImageRegistry as ApiImageRegistry

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (navigate_and_get_rows, ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView, click_row)
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator


class ImageRegistryAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Image Registries"


class ImageRegistryDetailsView(ContainerObjectDetailsBaseView):
    pass


class ImageRegistry(WidgetasticTaggable, Navigatable):

    PLURAL = 'Image Registries'
    all_view = ImageRegistryAllView
    details_view = ImageRegistryDetailsView

    def __init__(self, host, provider, appliance=None):
        self.host = host
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

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


@navigator.register(ImageRegistry, 'All')
class ImageRegistryAll(CFMENavigateStep):
    VIEW = ImageRegistryAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Image Registries')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(ImageRegistry, 'Details')
class ImageRegistryDetails(CFMENavigateStep):
    VIEW = ImageRegistryDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        click_row(self.prerequisite_view, host=self.obj.host)


@navigator.register(ImageRegistry, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
