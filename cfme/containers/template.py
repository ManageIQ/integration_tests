# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.common import Taggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView, GetRandomInstancesMixin)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from cfme.utils.providers import get_crud_by_name


class TemplateAllView(ContainerObjectAllBaseView):
    """Container Templates All view"""
    SUMMARY_TEXT = "Container Templates"


class TemplateDetailsView(ContainerObjectDetailsBaseView):
    """Container Templates Details view"""
    SUMMARY_TEXT = "Container Templates"


@attr.s
class Template(BaseEntity, Taggable, Labelable):

    PLURAL = 'Templates'
    all_view = TemplateAllView
    details_view = TemplateDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()


@attr.s
class TemplateCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Template`."""

    ENTITY = Template

    def all(self):
        # container_templates table has ems_id, join with ext_mgmgt_systems on id for provider name
        # Then join with container_projects on the id for the project
        template_table = self.appliance.db.client['container_templates']
        ems_table = self.appliance.db.client['ext_management_systems']
        project_table = self.appliance.db.client['container_projects']
        template_query = (
            self.appliance.db.client.session
                .query(template_table.name, project_table.name, ems_table.name)
                .join(ems_table, template_table.ems_id == ems_table.id)
                .join(project_table, template_table.container_project_id == project_table.id))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            template_query = template_query.filter(ems_table.name == provider.name)
        templates = []
        for name, project_name, ems_name in template_query.all():
            templates.append(self.instantiate(name=name, project_name=project_name,
                                              provider=provider or get_crud_by_name(ems_name)))

        return templates


@navigator.register(TemplateCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = TemplateAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Templates')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Template, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = TemplateDetailsView

    def step(self):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(Template, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
