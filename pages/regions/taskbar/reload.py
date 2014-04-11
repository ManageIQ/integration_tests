# -*- coding: utf-8 -*-
""" Reload taskbar button mixin.

@author: Milan Falešník <mfalesni@redhat.com>
"""
from pages.page import Page
from selenium.webdriver.common.by import By


class ReloadMixin(Page):
    """ Very common button mixin

    """
    def reload(self):
        """ Reload the current view

        """
        selector = "div#miq_alone > img[src*='reload.png']"     # Must be reload.png because there
                                                                # can be other miq_alone-s (>_<)
        self._wait_for_visible_element(By.CSS_SELECTOR, selector, visible_timeout=5)
        refresh_button = self.selenium.find_element_by_css_selector(selector)
        refresh_button.click()
        self._wait_for_results_refresh()
        return self
