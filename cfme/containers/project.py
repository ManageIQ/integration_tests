import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling

from cfme.common import Taggable
from cfme.common import TaggableCollection
from cfme.common import TagPageView
from cfme.containers.provider import ContainerObjectAllBaseView
from cfme.containers.provider import ContainerObjectDetailsBaseView
from cfme.containers.provider import GetRandomInstancesMixin
from cfme.containers.provider import Labelable
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.providers import get_crud_by_name


class ProjectAllView(ContainerObjectAllBaseView):
    """Container Projects All view"""
    SUMMARY_TEXT = 'Container Projects'


class ProjectDetailsView(ContainerObjectDetailsBaseView):
    """Container Projects Detail view"""
    SUMMARY_TEXT = 'Container Projects'


class ProjectDashboardView(ProjectDetailsView):

    @property
    def is_displayed(self):
        return(
            self.breadcrumb.is_displayed and
            '{} (Dashboard)'.format(self.context['object'].name) in self.breadcrumb.active_location)


@attr.s
class Project(BaseEntity, Taggable, Labelable):

    PLURAL = 'Projects'
    all_view = ProjectAllView
    details_view = ProjectDetailsView

    name = attr.ib()
    provider = attr.ib()


@attr.s
class ProjectCollection(GetRandomInstancesMixin, BaseCollection, TaggableCollection):
    """Collection object for :py:class:`Project`."""

    ENTITY = Project

    def all(self):
        # container_projects table has ems_id, join with ext_mgmgt_systems on id for provider name
        # TODO Update to use REST API instead of DB queries
        project_table = self.appliance.db.client['container_projects']
        ems_table = self.appliance.db.client['ext_management_systems']
        project_query = (
            self.appliance.db.client.session
                .query(project_table.name, ems_table.name)
                .join(ems_table, project_table.ems_id == ems_table.id))
        if self.filters.get('archived'):
            project_query = project_query.filter(project_table.deleted_on.isnot(None))
        if self.filters.get('active'):
            project_query = project_query.filter(project_table.deleted_on.is_(None))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            project_query = project_query.filter(ems_table.name == provider.name)
        projects = []
        for name, ems_name in project_query.all():
            projects.append(self.instantiate(name=name,
                                             provider=provider or get_crud_by_name(ems_name)))

        return projects


@navigator.register(ProjectCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ProjectAllView

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Projects')

    def resetter(self, *args, **kwargs):
        # Reset view and selection
        if self.view.toolbar.view_selector.is_displayed:
            self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.reset_selection()


@navigator.register(Project, 'Details')
class Details(CFMENavigateStep):
    VIEW = ProjectDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()

    def resetter(self, *args, **kwargs):
        if self.view.toolbar.view_selector.is_displayed:
            self.view.toolbar.view_selector.select("Summary View")


@navigator.register(Project, 'Dashboard')
class Dashboard(CFMENavigateStep):
    VIEW = ProjectDashboardView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()

    def resetter(self, *args, **kwargs):
        if self.view.toolbar.view_selector.is_displayed:
            self.view.toolbar.view_selector.select("Dashboard View")


@navigator.register(Project, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(Project, 'EditTagsFromDashboard')
class EditTagsFromDashboard(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Dashboard')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
