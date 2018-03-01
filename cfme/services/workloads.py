# -*- coding: utf-8 -*-
""" A model of Workloads page in CFME
"""
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from cfme.utils.appliance import Navigatable
from cfme.base.ui import WorkloadsView
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class WorkloadsVM(WorkloadsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_workloads and
            self.title.text == 'All VMs & Instances' and
            self.vms.is_opened and
            self.vms.tree.currently_selected == [
                "All VMs & Instances"])


class WorkloadsTemplate(WorkloadsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_workloads and
            self.title.text == 'All Templates & Images' and
            self.templates.is_opened and
            self.templates.tree.currently_selected == [
                "All Templates & Images"])


class VmsInstances(Navigatable):
    """
        This is fake class mainly needed for navmazing navigation

    """
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)


class TemplatesImages(Navigatable):
    """
        This is fake class mainly needed for navmazing navigation

    """

    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)


@navigator.register(VmsInstances, 'All')
class AllVMs(CFMENavigateStep):
    VIEW = WorkloadsVM
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Workloads')
        self.view.search.clear_simple_search()
        self.view.vms.clear_filter()


@navigator.register(TemplatesImages, 'All')
class AllTemplates(CFMENavigateStep):
    VIEW = WorkloadsTemplate
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Workloads')
        self.view.search.clear_simple_search()
        self.view.templates.clear_filter()
