# -*- coding: utf-8 -*-
""" A model of Workloads page in CFME
"""
from navmazing import NavigateToAttribute
from widgetastic.widget import View, Text
from widgetastic_manageiq import Accordion, ManageIQTree, Search

from cfme import BaseLoggedInPage
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep


class WorkloadsView(BaseLoggedInPage):
    search = View.nested(Search)

    def in_workloads(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Services', 'Workloads'])

    @View.nested
    class vms(Accordion):
        ACCORDION_NAME = "VMs & Instances"
        tree = ManageIQTree()

        def select_global_filter(self, filter_name):
            self.tree.click_path("All VMs & Instances", "Global Filters", filter_name)

        def select_my_filter(self, filter_name):
            self.tree.click_path("All VMs & Instances", "My Filters", filter_name)

        def clear_filter(self):
            self.parent.search.clear_search()
            self.tree.click_path("All VMs & Instances")

    @View.nested
    class templates(Accordion):
        ACCORDION_NAME = "Templates & Images"
        tree = ManageIQTree()

        def select_global_filter(self, filter_name):
            self.tree.click_path("All Templates & Images", "Global Filters", filter_name)

        def select_my_filter(self, filter_name):
            self.tree.click_path("All Templates & Images", "My Filters", filter_name)

        def clear_filter(self):
            self.parent.search.clear_search()
            self.tree.click_path("All Templates & Images")


class WorkLoadsVM(WorkloadsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            super(WorkLoadsVM, self).is_displayed and
            self.title.text == 'All VMs & Instances' and
            self.vms.is_opened and
            self.vms.tree.currently_selected == [
                "All VMs & Instances"])


class WorkLoadsTemplate(WorkloadsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            super(WorkLoadsTemplate, self).is_displayed and
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
    VIEW = WorkLoadsVM
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        workloads = self.create_view(WorkloadsView)
        self.prerequisite_view.navigation.select('Services', 'Workloads')
        workloads.search.clear_search()
        workloads.vms.clear_filter()

    def am_i_here(self, *args, **kwargs):
        self.view.is_displayed()


@navigator.register(TemplatesImages, 'All')
class AllTemplates(CFMENavigateStep):
    VIEW = WorkLoadsTemplate
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        workloads = self.create_view(WorkloadsView)
        self.prerequisite_view.navigation.select('Services', 'Workloads')
        workloads.search.clear_search()
        workloads.templates.clear_filter()

    def am_i_here(self, *args, **kwargs):
        self.view.is_displayes()
