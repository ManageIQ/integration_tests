# -*- coding: utf-8 -*-
import attr
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToAttribute, NavigateToSibling
from wrapanapi.containers.template import Template as ApiTemplate

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from cfme.utils.providers import get_crud_by_name


class TemplateAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Container Templates"


class TemplateDetailsView(ContainerObjectDetailsBaseView):
    pass


@attr.s
class Template(BaseEntity, WidgetasticTaggable, Labelable):

    PLURAL = 'Templates'
    all_view = TemplateAllView
    details_view = TemplateDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiTemplate(self.provider.mgmt, self.name, self.project_name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        template_list = provider.mgmt.list_template()
        random.shuffle(template_list)
        return [cls(obj.name, obj.project_name, provider, appliance=appliance)
                for obj in itertools.islice(template_list, count)]


@attr.s
class TemplateCollection(BaseCollection):
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
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name).click()


@navigator.register(Template, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
