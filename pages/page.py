#!/usr/bin/env python
# -*- coding: utf-8 -*-
from unittestzero import Assert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotVisibleException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time

class Page(object):
    '''
    Base class for all Pages
    '''
    _updating_locator = (By.CSS_SELECTOR, "div#notification > div:first-child")

    def __init__(self, testsetup, root=None):
        '''
        Constructor
        '''
        self.testsetup = testsetup
        self.base_url = testsetup.base_url
        self.selenium = testsetup.selenium
        self.timeout = testsetup.timeout
        if root is not None:
            self._root_element = root

    def _wait_for_results_refresh(self):
        # On pages that do not have ajax refresh this wait will have no effect.
        WebDriverWait(self.selenium, self.timeout).until(
                lambda s: not self.is_element_visible(*self._updating_locator))

    def _wait_for_visible_element(self, by, location, visible_timeout=None):
        """ Wait for an element to appear visible.

        Used in forms where an element (submit button) is displayed after ajax
        validation is done, this validation request doesn't use the common
        notification loadmask so _wait_for_results_refresh can't be used.
        On pages that do not have ajax refresh this wait will have no effect.

        @param by: What method (By.XPATH, By.CSS_SELECTOR, ...)
        @param location: Locator
        @keyword visible_timeout: Override standard timeout.
        """
        WebDriverWait(self.selenium, visible_timeout or self.timeout)\
            .until(lambda s: self.is_element_visible(by, location))

    @property
    def is_the_current_page(self):
        if self._page_title:  # IGNORE:E1101
            WebDriverWait(self.selenium, self.timeout).until(
                    lambda s: self.selenium.title)

        Assert.equal(self.selenium.title, self._page_title,  # IGNORE:E1101
            "Expected page title: %s. Actual page title: %s" %
            (self._page_title, self.selenium.title))  # IGNORE:E1101
        return True

    def get_url_current_page(self):
        WebDriverWait(self.selenium, self.timeout).until(
                lambda s: self.selenium.title)
        return self.selenium.current_url

    def get_context_current_page(self):
        url = self.get_url_current_page()
        stripped = url.lstrip('https://')
        return stripped[stripped.find('/'):stripped.rfind('?')]

    def is_element_present(self, *locator):
        self.selenium.implicitly_wait(0)
        try:
            self.selenium.find_element(*locator)
            return True
        except NoSuchElementException:
            return False
        finally:
            # set back to where you once belonged
            self.selenium.implicitly_wait(self.testsetup.default_implicit_wait)

    def is_element_visible(self, *locator):
        try:
            return self.selenium.find_element(*locator).is_displayed()
        except NoSuchElementException, ElementNotVisibleException:
            return False

    def return_to_previous_page(self):
        self.selenium.back()

    def get_element(self, *element):
        return self.selenium.find_element(*element)

    def handle_popup(self, cancel=False):
        wait = WebDriverWait(self.selenium, self.timeout)
        # throws timeout exception if not found
        wait.until(EC.alert_is_present())
        popup = self.selenium.switch_to_alert()
        answer = 'cancel' if cancel else 'ok'
        print popup.text + " ...clicking " + answer
        popup.dismiss() if cancel else popup.accept()

    def fill_field_element_with_wait(self, data, field_element):
        field_element = self.fill_field_element(data,field_element)
        # Stupid wait for ajax interval
        time.sleep(2)
        return field_element

    def fill_field_element_clears_text(self, data, field_element):
        '''Fill field with workaround for javascript clearing behavior'''
        field_element.click()
        time.sleep(1)
        field_element.clear()
        field_element.send_keys(data)

    def fill_field_element(self, data, field_element):
        field_element.clear()
        field_element.send_keys(data)
        return field_element

    def fill_field_by_locator(self, data, *locator):
        field_element = self.get_element(*locator)
        self.fill_field_element(data, field_element)
        return field_element

    def fill_field_by_locator_with_wait(self, data, *locator):
        field_element = self.get_element(*locator)
        self.fill_field_element_with_wait(data, field_element)
        return field_element

    def select_dropdown(self, value, *element):
        select = Select(self.selenium.find_element(*element))
        select.select_by_visible_text(value)

    def select_dropdown_by_value(self, value, *element):
        select = Select(self.selenium.find_element(*element))
        select.select_by_value(value)

