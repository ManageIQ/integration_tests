# -*- coding: utf-8 -*-


class Browser(object):
    """Equivalent of pytest_selenium - browser functions"""
    def __init__(self, selenium_browser):
        self.selenium = selenium_browser

    def elements(self, locator, parent=None):
        pass

    def element(self, locator, parent=None):
        pass

    # So on ...
