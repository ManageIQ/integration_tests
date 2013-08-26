# -*- coding: utf-8 -*-
from pages.page import Page
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from unittestzero import Assert
from random import choice

class Taggable(Page):
    '''Add this mixin to your page in 3 easy steps:
        * import: from pages.regions.taggable import Taggable
        * add to class: class MyClass(Base, Taggable):
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

    def assign_tags_and_save(self, tags):
        '''Service method to assign tags and save'''
        self.assign_tags(tags)
        return self.save_tag_edits()

    def assign_tags(self, tags):
        '''Assign list of key, value tags'''

        for category, value in tags.iteritems():
            self.select_category(category)
            self.select_value(value)
            Assert.true(self.is_tag_displayed(category, value))

    def select_category(self, category):
        '''Select tag category'''
        self._wait_for_visible_element(*self._tag_category_selector)
        self.select_dropdown(category, *self._tag_category_selector)
        self._wait_for_results_refresh()

    def select_value(self, value):
        '''Select tag value'''
        self._wait_for_visible_element(*self._tag_value_selector)
        self.select_dropdown(value, *self._tag_value_selector)
        self._wait_for_results_refresh()

    @property
    def categories_dropdown(self):
        ''' New tag category dropdown '''
        return Select(self.selenium.find_element(*self._tag_category_selector))

    @property
    def category_values_dropdown(self):
        ''' Values dropdown for adding a tag '''
        return Select(self.selenium.find_element(*self._tag_value_selector))

    @property
    def available_categories(self):
        ''' Get a list of current available categories that could be assigned '''
        return [option.text for option in self.categories_dropdown.options]

    def category_values(self, category):
        ''' Get a list of current available values for a particular category '''
        self.select_category(category)
        values = []
        for option in self.category_values_dropdown.options:
            if "<Select" not in option.text: 
                values.append(option.text)
        return values

    def add_random_tag(self):
        ''' Add a random tag 

        Returns the category and value text as strings '''

        still_searching = True
        while still_searching:
            # For some reason, several options in the dropdown have a "  " that 
            #    is not seen in the current tags table
            cat_text = choice(self.available_categories).replace("  ", " ")
            value_text = choice(self.category_values(cat_text))
            # multiple runs may assign all the values 
            #    which would result in a error, pick again if we hit that
            if "<All values are assigned>" not in value_text:
                still_searching = False
        self.assign_tags( { cat_text: value_text } )
        return cat_text, value_text

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

    def save_tag_edits(self):
        self._wait_for_visible_element(*self._save_edits_button)
        self.selenium.find_element(*self._save_edits_button).click()
        return self._wait_for_results_refresh()

    def cancel_tag_edits(self):
        self._wait_for_visible_element(*self._cancel_edits_button)
        self.selenium.find_element(*self._cancel_edits_button).click()
        return self._wait_for_results_refresh()

    def reset_tag_edits(self):
        self._wait_for_visible_element(*self._reset_edits_button)
        self.selenium.find_element(*self._reset_edits_button).click()
        return self._wait_for_results_refresh()
