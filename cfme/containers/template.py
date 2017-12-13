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
    prerequisite = NavigateToSibling('parent', 'All')
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
