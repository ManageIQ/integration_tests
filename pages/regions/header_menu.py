#!/usr/bin/env python

# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.page import Page
from pages.infrastructure import Infrastructure
from pages.services import Services
from pages.automate import Automate
from pages.control import Control
from pages.configuration import Configuration
from pages.configuration_subpages.tasks_tabs import Tasks
from pages.infrastructure_subpages.vms_subpages.virtual_machines import VirtualMachines
from pages.virtual_intelligence import VirtualIntelligence
from pages.optimize import Optimize
from pages.infrastructure_subpages.providers import Providers
from pages.infrastructure_subpages.hosts import Hosts

class HeaderMenu(Page):
    """
    This class accesses the header area from the top-level Page.
    To access:
        HeaderMenu(self.testsetup, element_lookup)
    Where element_lookup is:
        * the web element of the menu you want
    Example:
        HeaderMenu(self.testsetup, infrastructure_element) returns the Infrastructure menu
    """

    _menu_items_locator = (By.CSS_SELECTOR, 'ul > li')
    _name_locator = (By.CSS_SELECTOR, 'a')
    _item_page = {"Virtual Intelligence": VirtualIntelligence,
                  "Services": Services,
                  "Infrastructure": Infrastructure,
                  "Control": Control,
                  "Automate": Automate,
                  "Optimize": Optimize,
                  "Configure": Configuration}
    def __init__(self, testsetup, element):
        Page.__init__(self, testsetup)
        self._root_element = element

    @property
    def name(self):
        # The page is encoded in UTF-8. Convert to it.
        name = self._root_element.find_element(
                *self._name_locator).text.encode('utf-8')
        if not name:
            # If name is empty, assume Configuration menu
            name = "Configuration"
        return name

    def click(self):
        name = self.name
        self._root_element.find_element(*self._name_locator).click()
        current_subpage = self._item_page[name](self.testsetup).current_subpage
        if current_subpage is None:
            current_subpage = Page(self.testsetup)
        return current_subpage

    def hover(self):
        element = self._root_element.find_element(*self._name_locator)
        # Workaround for Firefox
        chain = ActionChains(self.selenium).move_to_element(element)
        if "firefox" in self.selenium.desired_capabilities["browserName"]:
            chain.move_by_offset(0, element.size['height'])
        chain.perform()

    @property
    def is_menu_submenu_visible(self):
        submenu = self._root_element.find_element(*self._menu_items_locator)
        return submenu.is_displayed()

    def sub_navigation_menu(self, value):
        # used to access on specific menu
        for menu in self.items:
            if menu.name == value:
                return menu
        raise Exception("Menu not found: '%s'. Menus: %s" % (
                value, [menu.name for menu in self.items]))

    @property
    def items(self):
        return [self.HeaderMenuItem(self.testsetup, web_element, self)
                for web_element in self._root_element.find_elements(
                        *self._menu_items_locator)]

    class HeaderMenuItem(Page):
        _name_locator = (By.CSS_SELECTOR, 'a')
        # The first level of the dictionary is the top-level menu item.
        # The second level is the sub page
        _item_page = {
            "Virtual Intelligence": {
                #"Dashboard":
                "Reports": VirtualIntelligence.Reports,
                #"Usage":
                "Chargeback": VirtualIntelligence.Chargeback,
                #"Timelines":
                #"RSS":
            },
            "Services": {
                "My Services": Services.MyServices,
                "Catalogs": Services.Catalogs,
                #"Requests":
                #"Workloads":
            },
            "Cloud": {
                #"Providers":
                #"Availability Zones":
                #"Flavors":
                #"Instances":
            },
            "Infrastructure": {
                "Providers" : Providers,
                "Clusters": Infrastructure.Clusters,
                "Hosts": Hosts,
                "Virtual Machines": VirtualMachines,
                #"Resource Pools":
                "Datastores": Infrastructure.Datastores,
                #"Repositories":
                "PXE": Infrastructure.PXE,
                #"Requests"
            },
            "Control": {
                "Explorer": Control.Explorer,
                #"Simulation":
                "Import / Export": Control.ImportExport,
                #"Log":
            },
            "Automate": {
                "Explorer": Automate.Explorer,
                #"Simulation":
                "Customization": Automate.Customization,
                "Import / Export": Automate.ImportExport,
                #"Log":
                #"Requests":
            },
            "Optimize": {
                "Utilization": Optimize.Utilization,
                #"Planning":
                #"Bottlenecks":
            },
            "Configure": {
                "My Settings": Configuration.MySettings,
                "Tasks": Tasks.MyVmAnalysisTasks,
                "Configuration": Configuration.Configuration,
                "SmartProxies": Configuration.SmartProxies,
                "About": Configuration.About,
            },
        }

        def __init__(self, testsetup, element, menu):
            Page.__init__(self, testsetup)
            self._root_element = element
            self._menu = menu

        @property
        def name(self):
            self._menu.hover()
            return self._root_element.find_element(
                    *self._name_locator).text.encode('utf-8')

        def click(self):
            menu_name = self._menu.name
            self._menu.hover()
            my_name = self.name
            ActionChains(self.selenium).move_to_element(
                    self._root_element).click().perform()

            return self._item_page[menu_name][my_name](self.testsetup)
