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
        for tile in quadicons:
            if tile.find_elements_by_css_selector('a')[1].get_attribute('title') == title:
                return tile

    class QuadiconItem(Page):
        _quadlink_locator = (By.CSS_SELECTOR, '#quadicon > a:nth-child(0)')
	    _checkbox_locator = (By.CSS_SELECTOR, '#listcheckbox')
	    _label_link_locator = (By.CSS_SELECTOR, 'a:nth-child(1)')
	    _quad_tl_locator = (By.CSS_SELECTOR, '#quadicon > div:nth-child(1)')
	    _quad_tr_locator = (By.CSS_SELECTOR, '#quadicon > div:nth-child(2)')
	    _quad_bl_locator = (By.CSS_SELECTOR, '#quadicon > div:nth-child(3)')
	    _quad_br_locator = (By.CSS_SELECTOR, '#quadicon > div:nth-child(4)')

        def __init__(self, testsetup, quadicon_list_element):
            Page.__init__(self, testsetup)
            self._root_element = quadicon_list_element

        def click(self):
            self._root_element.find_element(*self._quadlink_locator).click()

        @property
        def title(self):
            return self._root_element._quadlink_locator.title

        @property
        def name(self):
            return self._root_element._quadlink_locator.title

        @property
        def href_value(self):
            return self._root_element.find_element(*self._quadlink_locator).get_attribute('href')

        @property
        def is_selected():
	    return self._root_element.find_element(*self._checkbox_locator).is_selected()

        def markCheckbox(self):
            if not self.is_selected():
                self._root_element.find_element(*self._checkbox_locator).click()

        def unmarkCheckbox(self):
            if self.is_selected():
                self._root_element.find_element(*self._checkbox_locator).click()
