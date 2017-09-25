# -*- coding: utf-8 -*-
import random
import itertools
from cached_property import cached_property

from wrapanapi.containers.project import Project as ApiProject

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView, click_row)
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from navmazing import NavigateToAttribute, NavigateToSibling


class ProjectAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Projects"


class ProjectDetailsView(ContainerObjectDetailsBaseView):
    pass


class Project(WidgetasticTaggable, Labelable, Navigatable):

    PLURAL = 'Projects'
    all_view = ProjectAllView
    details_view = ProjectDetailsView

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    @cached_property
    def mgmt(self):
        return ApiProject(self.provider.mgmt, self.name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        project_list = provider.mgmt.list_project()
        random.shuffle(project_list)
        return [cls(obj.name, provider, appliance=appliance)
                for obj in itertools.islice(project_list, count)]


@navigator.register(Project, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ProjectAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Projects')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(Project, 'Details')
class Details(CFMENavigateStep):
    VIEW = ProjectDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        click_row(self.prerequisite_view, Name=self.obj.name)


@navigator.register(Project, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
