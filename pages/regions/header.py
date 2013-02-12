#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

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
