# -*- coding: utf-8 -*-
""" A model of Workloads page in CFME
"""
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import View, Text
from widgetastic_manageiq import Accordion, ManageIQTree, Search

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import Navigatable
from cfme.base import Server
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class WorkloadsView(BaseLoggedInPage):
    search = View.nested(Search)

    @property
    def in_workloads(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Services', 'Workloads'])

    @View.nested
    class vms(Accordion):  # noqa
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
    class templates(Accordion):  # noqa
        ACCORDION_NAME = "Templates & Images"
        tree = ManageIQTree()

        def select_global_filter(self, filter_name):
            self.tree.click_path("All Templates & Images", "Global Filters", filter_name)

        def select_my_filter(self, filter_name):
            self.tree.click_path("All Templates & Images", "My Filters", filter_name)

        def clear_filter(self):
            self.parent.search.clear_search()
            self.tree.click_path("All Templates & Images")


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


class WorkloadsDefaultView(WorkloadsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_workloads and
            self.title.text == 'All VMs & Instances' and
            self.vms.is_opened)


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


@navigator.register(Server)
class WorkloadsDefault(CFMENavigateStep):
    VIEW = WorkloadsDefaultView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Services", "Workloads")


@navigator.register(VmsInstances, 'All')
class AllVMs(CFMENavigateStep):
    VIEW = WorkloadsVM
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Workloads')
        self.view.search.clear_search()
        self.view.vms.clear_filter()


@navigator.register(TemplatesImages, 'All')
class AllTemplates(CFMENavigateStep):
    VIEW = WorkloadsTemplate
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Workloads')
        self.view.search.clear_search()
        self.view.templates.clear_filter()
