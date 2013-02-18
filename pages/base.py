#!/usr/bin/env python

# -*- coding: utf-8 -*-

from selenium.webdriver.support.ui import WebDriverWait
from pages.page import Page
from selenium.webdriver.common.by import By

class Base(Page):
    '''
    Base class for global project specific functions
    '''
    @property
    def page_title(self):
        WebDriverWait(self.selenium, self.timeout).until(lambda s: self.selenium.title)
        return self.selenium.title

    @property
    def header(self):
        return Base.HeaderRegion(self.testsetup)

    @property
    def is_logged_in(self):
        return self.header.is_logout_visible

    def go_to_login_page(self):
        self.selenium.get(self.base_url)

    class HeaderRegion(Page):
        # LoggedIn
        _logout_link_locator = (By.CSS_SELECTOR, "#time a")

        _site_navigation_menus_locator = (By.CSS_SELECTOR, "div.navbar > ul > li:not(.nav-doc)")
        _site_navigation_min_number_menus = 8

        @property
        def is_logout_visible(self):
            return self.is_element_visible(*self._logout_link_locator)

        def logout(self):
            self.selenium.find_element(*self._logout_link_locator).click()

        def site_navigation_menu(self, value):
            # used to access on specific menu
            for menu in self.site_navigation_menus:
                if menu.name == value:
                    return menu
            raise Exception("Menu not found: '%s'. Menus: %s" % (value, [menu.name for menu in self.site_navigation_menus]))

        @property
        def site_navigation_menus(self):
            # returns a list containing all the site navigation menus
            WebDriverWait(self.selenium, self.timeout).until(
                    lambda s: len(s.find_elements(*self._site_navigation_menus_locator))
                    >= self._site_navigation_min_number_menus)
            from pages.regions.header_menu import HeaderMenu
            return [HeaderMenu(self.testsetup, web_element) for web_element in self.selenium.find_elements(*self._site_navigation_menus_locator)]


