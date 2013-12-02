# -*- coding: utf-8 -*-
from pages.page import Page


class RefreshMixin(Page):
    """ Very common button mixin

    """
    def refresh(self):
        selector = "div#miq_alone > img[src*='reload.png']"     # Must be reload.png because there
                                                                # can be other miq_alone-s (>_<)
        refresh_button = self.selenium.find_element_by_css_selector(selector)
        refresh_button.click()
        self._wait_for_results_refresh()
        return self
