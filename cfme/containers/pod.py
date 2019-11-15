import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import View

from cfme.common import Taggable
from cfme.common import TaggableCollection
from cfme.common import TagPageView
from cfme.containers.provider import ContainerObjectAllBaseView
from cfme.containers.provider import ContainerObjectDetailsBaseView
from cfme.containers.provider import ContainerObjectDetailsEntities
from cfme.containers.provider import GetRandomInstancesMixin
from cfme.containers.provider import Labelable
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.providers import get_crud_by_name
from widgetastic_manageiq import NestedSummaryTable


class PodAllView(ContainerObjectAllBaseView):
    """Container Pods All view"""
    SUMMARY_TEXT = 'Container Pods'


class PodDetailsView(ContainerObjectDetailsBaseView):
    """Container Pods Detail view"""
    SUMMARY_TEXT = 'Container Pods'

    @View.nested
    class entities(ContainerObjectDetailsEntities):  # noqa
        volumes = NestedSummaryTable(title='Volumes')
        conditions = NestedSummaryTable(title='Conditions')


@attr.s
class Pod(BaseEntity, Taggable, Labelable):
    """Pod Class"""
    PLURAL = 'Pods'
    all_view = PodAllView
    details_view = PodDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()


@attr.s
class PodCollection(GetRandomInstancesMixin, BaseCollection, TaggableCollection):
    """Collection object for :py:class:`Pod`."""

    ENTITY = Pod

    def all(self):
        # container_groups table has ems_id, join with ext_mgmgt_systems on id for provider name
        # Then join with container_projects on the id for the project
        # TODO Update to use REST API instead of DB queries
        pod_table = self.appliance.db.client['container_groups']
        ems_table = self.appliance.db.client['ext_management_systems']
        project_table = self.appliance.db.client['container_projects']
        pod_query = (
            self.appliance.db.client.session
                .query(pod_table.name, project_table.name, ems_table.name)
                .join(ems_table, pod_table.ems_id == ems_table.id)
                .join(project_table, pod_table.container_project_id == project_table.id))
        if self.filters.get('archived'):
            pod_query = pod_query.filter(pod_table.deleted_on.isnot(None))
        if self.filters.get('active'):
            pod_query = pod_query.filter(pod_table.deleted_on.is_(None))
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

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Pods')

    def resetter(self, *args, **kwargs):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Pod, 'Details')
class Details(CFMENavigateStep):
    VIEW = PodDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(Pod, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
