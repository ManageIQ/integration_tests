# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute

from cfme.modeling.base import BaseCollection
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator


@attr.s
class TopologyCollection(BaseCollection):
    pass


@navigator.register(TopologyCollection, 'All')
class All(CFMENavigateStep):

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Topology')
