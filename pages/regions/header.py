#!/usr/bin/env python

from selenium.webdriver.support.ui import WebDriverWait
from pages.page import Page
from selenium.webdriver.common.by import By

class HeaderRegion(Page):
    _logout_link_locator = (By.CSS_SELECTOR, "#time a")

    @property
    def is_logout_visible(self):
        return self.is_element_visible(*self._logout_link_locator)

    def logout(self):
        self.selenium.find_element(*self._logout_link_locator).click()
