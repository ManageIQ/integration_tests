# -*- coding: utf-8 -*-
from pages.page import Page


class RefreshMixin(Page):
    """ Very common button mixin

    """
    def refresh(self):
        refresh_button = self.selenium.find_element_by_css_selector("div#miq_alone > img")
        refresh_button.click()
        self._wait_for_results_refresh()
        return self
