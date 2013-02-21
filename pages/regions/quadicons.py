# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By

from pages.page import Page


class Quadicons(Page):
    _quadicons_locator = (By.CSS_SELECTOR, "#records_div > table > tbody > tr > td > div")

    @property
    def quadicons(self):
        return [self.QuadiconItem(self.testsetup, quadicon_list_item)
                for quadicon_list_item in self.selenium.find_elements(*self._quadicons_locator)]

    def get_quadicon_by_title(self, title):
        for tile in self.quadicons:
            if tile.find_elements_by_css_selector('a')[1].get_attribute('title') == title:
                return tile

    class QuadiconItem(Page):
        _quadlink_locator = (By.CSS_SELECTOR, '#quadicon > div > a')
        _checkbox_locator = (By.CSS_SELECTOR, '#listcheckbox')
        _label_link_locator = (By.CSS_SELECTOR, 'tr > td > a')
        _quad_tl_locator = (By.CSS_SELECTOR, '#quadicon > div.a72')
        _quad_tr_locator = (By.CSS_SELECTOR, '#quadicon > div.b72')
        _quad_bl_locator = (By.CSS_SELECTOR, '#quadicon > div.c72')
        _quad_br_locator = (By.CSS_SELECTOR, '#quadicon > div.d72')

        def __init__(self, testsetup, quadicon_list_element):
            Page.__init__(self, testsetup)
            self._root_element = quadicon_list_element

        def click(self):
            self._root_element.find_element(*self._quadlink_locator).click()

        @property
        def title(self):
            return self._root_element.find_element(*self._quadlink_locator).get_attribute('title')

        @property
        def name(self):
            return self._root_element.find_element(*self._label_link_locator).text

        @property
        def href_value(self):
            return self._root_element.find_element(*self._quadlink_locator).get_attribute('href')

        @property
        def is_selected(self):
            return self._root_element.find_element(*self._checkbox_locator).is_selected()

        def toggle_checkbox(self):
            self._root_element.find_element(*self._checkbox_locator).click()

        def mark_checkbox(self):
            if not self.is_selected:
                self.toggle_checkbox()

        def unmark_checkbox(self):
            if self.is_selected:
                self.toggle_checkbox()
