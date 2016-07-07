# -*- coding: utf-8 -*-


class Browser(object):
    def __init__(self, selenium_browser):
        self.selenium = selenium_browser

    def elements(self, locator, parents=()):
        pass

    def element(self, locator, parents=()):
        pass

    # So on ...
