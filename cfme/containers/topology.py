# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToAttribute

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.common import TopologyMixin
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to


class Topology(TopologyMixin, BaseEntity):

    @classmethod
    def load_topology_page(cls):
        navigate_to(cls, 'All')


@attr.s
class TopologyCollection(BaseCollection):
        ENTITY = Topology


@navigator.register(Topology, 'All')
class All(CFMENavigateStep):

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Topology')
