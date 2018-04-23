# -*- coding: utf-8 -*-
import attr
from cached_property import cached_property

from navmazing import NavigateToAttribute, NavigateToSibling
from wrapanapi.containers.project import Project as ApiProject

from cfme.common import Taggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView,
                                      GetRandomInstancesMixin)
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.providers import get_crud_by_name


class ProjectAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Projects"


class ProjectDetailsView(ContainerObjectDetailsBaseView):
    pass


@attr.s
class Project(BaseEntity, Taggable, Labelable):

    PLURAL = 'Projects'
    all_view = ProjectAllView
    details_view = ProjectDetailsView

    name = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiProject(self.provider.mgmt, self.name)

    @property
    def exists(self):
        """Return True if the Project exists"""
        # TODO: move this to some ContainerObjectBase so it'll be shared among all objects
        try:
            navigate_to(self, 'Details')
        except ItemNotFound:
            return False
        else:
            return True


@attr.s
class ProjectCollection(GetRandomInstancesMixin, BaseCollection):
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

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Projects')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.reset_selection()


@navigator.register(Project, 'Details')
class Details(CFMENavigateStep):
    VIEW = ProjectDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()

    def resetter(self):
        if self.appliance.version.is_in_series('5.9'):
            self.view.toolbar.view_selector.select("Summary View")


@navigator.register(Project, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
