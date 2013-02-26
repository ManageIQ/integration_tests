#!/usr/bin/env python

# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from pages.page import Page

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

    def __init__(self, testsetup, element):
        Page.__init__(self, testsetup)
        self._root_element = element

    @property
    def name(self):
        # FIXED: Select :not(.nav-doc)
        # TODO: File a bug :)
        # The page is encoded in UTF-8. Convert to it.
        return self._root_element.find_element(*self._name_locator).text.encode('utf-8')

    def click(self):
        name = self.name
        self._root_element.find_element(*self._name_locator).click()
        
        if "Virtual Intelligence" in name:
            pass
        elif "Services" in name:
            pass
        elif "Infrastructure" in name:
            from pages.infrastructure import Infrastructure
            return Infrastructure.ManagementSystems(self.testsetup)
        elif "VDI" in name:
            pass
        elif "Storage" in name:
            pass
        elif "Control" in name:
            pass
        elif "Automate" in name:
            pass
        elif "Optimize" in name:
            pass

    def hover(self):
        element = self._root_element.find_element(*self._name_locator)
        ActionChains(self.selenium).move_to_element(element).perform()

    @property
    def is_menu_submenu_visible(self):
        submenu = self._root_element.find_element(*self._menu_items_locator)
        return submenu.is_displayed()

    def sub_navigation_menu(self, value):
        # used to access on specific menu
        for menu in self.items:
            if menu.name == value:
                return menu
        raise Exception("Menu not found: '%s'. Menus: %s" % (value, [menu.name for menu in self.items]))

    @property
    def items(self):
        return [self.HeaderMenuItem(self.testsetup, web_element, self)
                for web_element in self._root_element.find_elements(*self._menu_items_locator)]

    class HeaderMenuItem(Page):
        _name_locator = (By.CSS_SELECTOR, 'a')

        def __init__(self, testsetup, element, menu):
            Page.__init__(self, testsetup)
            self._root_element = element
            self._menu = menu

        @property
        def name(self):
            self._menu.hover()
            return self._root_element.find_element(*self._name_locator).text.encode('utf-8')

        def click(self):
            menu_name = self._menu.name
            self._menu.hover()
            my_name = self.name
            ActionChains(self.selenium).move_to_element(self._root_element).click().perform()

            if "Management Systems" in my_name:
                from pages.infrastructure import Infrastructure
                return Infrastructure.ManagementSystems(self.testsetup)
            elif "PXE" in my_name:
                from pages.infrastructure import Infrastructure
                return Infrastructure.PXE(self.testsetup)
            elif "Virtual Machines" in my_name:
                from pages.services import Services
                return Services.VirtualMachines(self.testsetup)

