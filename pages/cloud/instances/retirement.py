# -*- coding: utf-8 -*-
# pylint: disable=R0904

from pages.base import Base
from selenium.webdriver.common.by import By

class Retirement(Base):
    """Class to set retirement dates of vms"""
    _date_edit_field_locator = (By.CSS_SELECTOR, "input#miq_date_1")
    _retirement_warning_edit_field_locator = (By.CSS_SELECTOR,
                        "select#retirement_warn")
    _save_button_locator = (By.CSS_SELECTOR,
                        "ul#form_buttons > li > img[title='Save Changes']")
    _cancel_button_locator = (By.CSS_SELECTOR,
                        "ul#form_buttons > li > img[title='Cancel']")
    _remove_retirement_date_button_locator = (By.ID, "remove_button")

    @property
    def date_field(self):
        return self.selenium.find_element(*self._date_edit_field_locator)

    @property
    def save_button(self):
        return self.get_element(*self._save_button_locator)

    @property
    def cancel_button(self):
        return self.get_element(*self._cancel_button_locator)

    @property
    def remove_button(self):
        return self.get_element(*self._remove_retirement_date_button_locator)

    def click_on_cancel(self):
        self._wait_for_visible_element(*self._cancel_button_locator)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        from pages.cloud.instances.details import Details
        return Details(self.testsetup)

    def click_on_save(self):
        self._wait_for_visible_element(*self._save_button_locator)
        self.save_button.click()
        self._wait_for_results_refresh()
        from pages.cloud.instances.details import Details
        return Details(self.testsetup)

    def click_on_remove(self):
        self._wait_for_visible_element(
            *self._remove_retirement_date_button_locator)
        self.remove_button.click()
        self._wait_for_results_refresh()
        return Retirement(self.testsetup)

    def fill_data(self, retirement_date, retirement_warning):
        if(retirement_date):
            self.date_field._parent.execute_script(
                "$j('#miq_date_1').attr('value', '%s')" % retirement_date)
            self._wait_for_results_refresh()

        if(retirement_warning):
            self.select_dropdown(retirement_warning,
                *self._retirement_warning_edit_field_locator)
            self._wait_for_results_refresh()
   