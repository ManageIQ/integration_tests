# -*- coding: utf-8 -*-
from pages.page import Page
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select

class TaggableMixin(Page):
    '''Add this mixin to your page in 3 easy steps:
        * import: from pages.regions.taggable import TaggableMixin
        * add to class: class MyClass(Base, TaggableMixin):
        * call directly from test or page
    
    '''
    #Navigation
    _tag_category_selector = (By.ID, "tag_cat")
    _tag_value_selector = (By.ID, "tag_add")
    _save_edits_button = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_edits_button = (By.CSS_SELECTOR, "img[title='Cancel']")
    _reset_edits_button = (By.CSS_SELECTOR, "img[title='Reset Changes']")

    #current tags table
    _tag_table = (By.CSS_SELECTOR, "div#assignments_div > table > tbody")
    _tag_row_locator = (By.XPATH, "tr")
    _tag_items_locator = (By.XPATH, "td")

    def select_category(self, category):
        self.select_dropdown(category, *self._tag_category_selector)
        self._wait_for_results_refresh()

    def select_value(self, value):
        self.select_dropdown(value, *self._tag_value_selector)
        self._wait_for_results_refresh()

    @property
    def root(self):
        return self.selenium.find_element(*self._tag_table).find_elements(*self._tag_row_locator)

    @property
    def current_tags(self):
        elements = [element.find_elements(*self._tag_items_locator) for element in self.root]
        tags = {category.text: (value.text, delete_element) for delete_element, category, value in elements}
        return tags

    def is_tag_displayed(self, category, value):
        if category in self.current_tags:
            return self.current_tags[category][0] == value
        else:
            return False

    def delete_tag(self, category):
        self.current_tags[category][1].click()
        return self._wait_for_results_refresh()

    @property
    def save_tag_edits(self):
        self._wait_for_visible_element(*self._save_edits_button)
        self.selenium.find_element(*self._save_edits_button).click()
        return self._wait_for_results_refresh()

    @property
    def cancel_tag_edits(self):
        self._wait_for_visible_element(*self._cancel_edits_button)
        self.selenium.find_element(*self._cancel_edits_button).click()
        return self._wait_for_results_refresh()

    @property
    def reset_tag_edits(self):
        self._wait_for_visible_element(*self._reset_edits_button)
        self.selenium.find_element(*self._reset_edits_button).click()
        return self._wait_for_results_refresh()
