# -*- coding: utf-8 -*-
from functools import partial
from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.web_ui import Quadicon, match_location, mixins
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.utils.appliance import Navigatable


match_page = partial(match_location, controller='cloud_object_store_container',
                     title='Object Stores')


class ObjectStore(Taggable, SummaryMixin, Navigatable):
    """ Automate Model page of Cloud Object Stores

    Args:
        name: Name of Object Store
    """

    def __init__(self, name=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.quad_name = 'object_store'

    def add_tag(self, tag, **kwargs):
        """Tags the system by given tag"""
        navigate_to(self, 'Details')
        mixins.add_tag(tag, **kwargs)

    def untag(self, tag):
        """Removes the selected tag off the system"""
        navigate_to(self, 'Details')
        mixins.remove_tag(tag)


@navigator.register(ObjectStore, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        if self.obj.appliance.version < "5.8":
            self.prerequisite_view.navigation.select('Storage', 'Object Stores')
        else:
            self.prerequisite_view.navigation.select(
                'Storage', 'Object Storage', 'Object Store Containers')

    def resetter(self):
        tb.select("Grid View")


@navigator.register(ObjectStore, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))
