#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.support.ui import WebDriverWait
from pages.page import Page
from selenium.webdriver.common.by import By

class Base(Page):
    '''
    Base class for global project specific functions
    '''
    @property
    def page_title(self):
        WebDriverWait(self.selenium, 10).until(lambda s: self.selenium.title)
        return self.selenium.title

    @property
    def header_region(self):
        from regions.header import HeaderRegion
        return HeaderRegion(self.testsetup)

    @property
    def main_navigation_region(self):
        from regions.main_navigation import MainNavigationRegion
        return MainNavigationRegion(self.testsetup)

    @property
    def is_logged_in(self):
        return self.header_region.is_logout_visible

    def go_to_login_page(self):
        self.selenium.get(self.base_url)

