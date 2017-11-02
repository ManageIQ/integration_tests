# -*- coding: utf-8 -*-
import random
import itertools
from cached_property import cached_property

from wrapanapi.containers.replicator import Replicator as ApiReplicator

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView, click_row)
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from navmazing import NavigateToAttribute, NavigateToSibling


class ReplicatorAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Replicators"


class ReplicatorDetailsView(ContainerObjectDetailsBaseView):
    pass


class Replicator(WidgetasticTaggable, Labelable, Navigatable):

    PLURAL = 'Replicators'
    all_view = ReplicatorAllView
    details_view = ReplicatorDetailsView

    def __init__(self, name, project_name, provider, appliance=None):
        self.name = name
        self.project_name = project_name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    @cached_property
    def mgmt(self):
        return ApiReplicator(self.provider.mgmt, self.name, self.project_name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        rc_list = provider.mgmt.list_replication_controller()
        random.shuffle(rc_list)
        return [cls(obj.name, obj.project_name, provider, appliance=appliance)
                for obj in itertools.islice(rc_list, count)]


@navigator.register(Replicator, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ReplicatorAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Replicators')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(Replicator, 'Details')
class Details(CFMENavigateStep):
    VIEW = ReplicatorDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        click_row(self.prerequisite_view,
                  name=self.obj.name, project_name=self.obj.project_name)


@navigator.register(Replicator, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
