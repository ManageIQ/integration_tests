# -*- coding: utf-8 -*-
import attr
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToAttribute, NavigateToSibling
from wrapanapi.containers.replicator import Replicator as ApiReplicator

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class ReplicatorAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Replicators"


class ReplicatorDetailsView(ContainerObjectDetailsBaseView):
    pass


@attr.s
class Replicator(BaseEntity, WidgetasticTaggable, Labelable):

    PLURAL = 'Replicators'
    all_view = ReplicatorAllView
    details_view = ReplicatorDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()

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


@attr.s
class ReplicatorCollection(BaseCollection):
    """Collection object for :py:class:`Replicator`."""

    ENTITY = Replicator


@navigator.register(ReplicatorCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ReplicatorAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Replicators')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Replicator, 'Details')
class Details(CFMENavigateStep):
    VIEW = ReplicatorDetailsView
    prerequisite = NavigateToSibling('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name).click()


@navigator.register(Replicator, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
