# -*- coding: utf-8 -*-
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToAttribute, NavigateToSibling
from wrapanapi.containers.pod import Pod as ApiPod
from widgetastic_manageiq import NestedSummaryTable, SummaryTable
from widgetastic.widget import View

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView, click_row, ContainerObjectDetailsEntities)
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class PodAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Pods"


class PodDetailsView(ContainerObjectDetailsBaseView):
    @View.nested
    class entities(ContainerObjectDetailsEntities):  # noqa
        volumes = NestedSummaryTable(title='Volumes')
        conditions = NestedSummaryTable(title='Conditions')
        container_statuses_summary = SummaryTable(title='Container Statuses Summary')


class Pod(WidgetasticTaggable, Labelable, Navigatable):

    PLURAL = 'Pods'
    all_view = PodAllView
    details_view = PodDetailsView

    def __init__(self, name, project_name, provider, appliance=None):
        self.name = name
        self.provider = provider
        self.project_name = project_name
        Navigatable.__init__(self, appliance=appliance)

    @cached_property
    def mgmt(self):
        return ApiPod(self.provider.mgmt, self.name, self.project_name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        pod_list = provider.mgmt.list_container_group()
        random.shuffle(pod_list)
        return [cls(obj.name, obj.project_name, provider, appliance=appliance)
                for obj in itertools.islice(pod_list, count)]


@navigator.register(Pod, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = PodAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Pods')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.check_all()
        self.view.paginator.uncheck_all()


@navigator.register(Pod, 'Details')
class Details(CFMENavigateStep):
    VIEW = PodDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        click_row(self.prerequisite_view,
                  name=self.obj.name, project_name=self.obj.project_name)


@navigator.register(Pod, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
