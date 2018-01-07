# -*- coding: utf-8 -*-
import attr
from cached_property import cached_property

from navmazing import NavigateToAttribute, NavigateToSibling
from wrapanapi.containers.pod import Pod as ApiPod
from widgetastic_manageiq import NestedSummaryTable, SummaryTable
from widgetastic.widget import View

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView,
                                      ContainerObjectDetailsEntities,
                                      GetRandomInstancesMixin)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from cfme.utils.providers import get_crud_by_name


class PodAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Pods"


class PodDetailsView(ContainerObjectDetailsBaseView):
    @View.nested
    class entities(ContainerObjectDetailsEntities):  # noqa
        volumes = NestedSummaryTable(title='Volumes')
        conditions = NestedSummaryTable(title='Conditions')
        container_statuses_summary = SummaryTable(title='Container Statuses Summary')


@attr.s
class Pod(BaseEntity, WidgetasticTaggable, Labelable):
    """Pod Class"""
    PLURAL = 'Pods'
    all_view = PodAllView
    details_view = PodDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiPod(self.provider.mgmt, self.name, self.project_name)


@attr.s
class PodCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Pod`."""

    ENTITY = Pod

    def all(self):
        # container_groups table has ems_id, join with ext_mgmgt_systems on id for provider name
        # Then join with container_projects on the id for the project
        pod_table = self.appliance.db.client['container_groups']
        ems_table = self.appliance.db.client['ext_management_systems']
        project_table = self.appliance.db.client['container_projects']
        pod_query = (
            self.appliance.db.client.session
                .query(pod_table.name, project_table.name, ems_table.name)
                .join(ems_table, pod_table.ems_id == ems_table.id)
                .join(project_table, pod_table.container_project_id == project_table.id))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            pod_query = pod_query.filter(ems_table.name == provider.name)
        pods = []
        for name, project_name, ems_name, in pod_query.all():
            pods.append(self.instantiate(name=name,
                                         project_name=project_name,
                                         provider=provider or get_crud_by_name(ems_name)))

        return pods


@navigator.register(PodCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = PodAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Pods')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Pod, 'Details')
class Details(CFMENavigateStep):
    VIEW = PodDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name,
                                                   use_search=True).click()

    def resetter(self):
        # Reset view and selection
        if self.appliance.version == '5.9':
            self.view.toolbar.view_selector.select("Summary View")


@navigator.register(Pod, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
