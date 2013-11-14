'''Created on July 25, 2013

@author: shveta
'''
from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time


class Customization(Base):
    '''Automate -Customization--Service Dialog'''
    _page_title = 'CloudForms Management Engine: Automate'
    _configuration_button_locator = (By.CSS_SELECTOR,
        "div.dhx_toolbar_btn[title='Configuration']")
    _add_dialog_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Add a new Dialog']")
    _del_dialog_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Remove this Dialog from the VMDB']")
    _edit_dialog_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Edit this Dialog']")
    _label_field = (By.CSS_SELECTOR, "input[name='label']")
    _edit_save_button = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _desc_field = (By.CSS_SELECTOR, "input[name='description']")
    _submit_button_checkbox = (By.CSS_SELECTOR, "input[name='chkbx_submit']")
    _cancel_button_checkbox = (By.CSS_SELECTOR, "input[name='chkbx_cancel']")
    _add_button = (By.CSS_SELECTOR, "img[title='Add']")
    _plus_button = (By.CSS_SELECTOR, "div.dhx_toolbar_arw[title='Add']")
    _add_tab_button = (By.CSS_SELECTOR,
        "tr.tr_btn[title='Add a New Tab to this Dialog']")
    _tab_label = (By.CSS_SELECTOR, "input[id='tab_label']")
    _tab_desc = (By.CSS_SELECTOR, "input[id='tab_description']")
    _add_box_button = (By.CSS_SELECTOR,
        "tr.tr_btn[title='Add a New Box to this Tab']")
    _box_label = (By.CSS_SELECTOR, "input[id='group_label']")
    _box_desc = (By.CSS_SELECTOR, "input[id='group_description']")
    _add_element_button = (By.CSS_SELECTOR,
        "tr.tr_btn[title='Add a New Element to this Box']")
    _ele_label = (By.CSS_SELECTOR, "input[id='field_label']")
    _ele_name = (By.CSS_SELECTOR, "input[id='field_name']")
    _ele_desc = (By.CSS_SELECTOR, "input[id='field_description']")
    _choose_type = (By.CSS_SELECTOR, "select#field_typ")
    _default_value_text_box = (By.CSS_SELECTOR, "input#field_default_value")

    @property
    def accordion(self):
        '''accordion'''
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
        return Accordion(self.testsetup, LegacyTreeAccordionItem)

    @property
    def configuration_button(self):
        '''Configuration button in service dialog page'''
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def _add_dialog_button(self):
        '''Add a new service dialog button'''
        return self.selenium.find_element(*self._add_dialog_button_locator)

    def add_new_service_dialog(self):
        '''Click on Configuration , add new service dialog'''
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self._add_dialog_button)\
            .perform()
        return Customization(self.testsetup)

    def click_on_service_dialog(self, service_dialog):
        '''Click on catalog to edit or delete'''
        self.accordion.current_content\
            .find_node_by_name(service_dialog).click()
        self._wait_for_results_refresh()
        return Customization(self.testsetup)

    @property
    def del_dialog_button(self):
        '''Delete catalog button'''
        return self.selenium.find_element(*self._del_dialog_button_locator)

    def delete_service_dialog(self):
        '''Delete catalog'''
        ActionChains(self.selenium).click(
            self.configuration_button).click(self.del_dialog_button).perform()
        self.handle_popup()
        self._wait_for_results_refresh()
        return Customization(self.testsetup)

    @property
    def _edit_dialog_button(self):
        '''Add a new service dialog button'''
        return self.selenium.find_element(*self._edit_dialog_button_locator)

    def edit_service_dialog(self, dialog_name):
        '''Click on Configuration , add new service dialog'''
        ActionChains(self.selenium).click(
            self.configuration_button).click(self._edit_dialog_button).perform()
        self.selenium.find_element(
            *self._label_field).send_keys(dialog_name)
        self._wait_for_visible_element(*self._edit_save_button)
        self.selenium.find_element(*self._edit_save_button).click()
        self._wait_for_results_refresh()
        return Customization(self.testsetup)

    def create_service_dialog(self, random_string, servicedialogname, desc, ele_name):
        '''fill service dialog form and sub forms'''
        self.add_label_to_dialog(servicedialogname, desc)
        self._wait_for_results_refresh()
        self.add_tab_to_dialog(
            random_string + "_tab_label", random_string + "_tab_desc")
        self.add_box_to_dialog(
            random_string + "_box_label", random_string + "_box_desc")
        time.sleep(3)
        self.add_element_to_dialog(
            random_string + "_ele_label",
            ele_name,
            "_ele_desc")
        self.save_dialog()
        return Customization(self.testsetup)

    def save_dialog(self):
        '''Save Service Dialog'''
        self._wait_for_visible_element(*self._add_button)
        self.selenium.find_element(*self._add_button).click()
        self._wait_for_results_refresh()
        return Customization(self.testsetup)

    def add_label_to_dialog(self, servicedialogname, desc):
        '''Add label'''
        self.selenium.find_element(
            *self._label_field).send_keys(servicedialogname)
        self.selenium.find_element(
            *self._desc_field).send_keys(desc)
        self.selenium.find_element(*self._submit_button_checkbox).click()
        self.selenium.find_element(*self._cancel_button_checkbox).click()
        return Customization(self.testsetup)

    def add_tab_to_dialog(self, tab_label, tab_desc):
        '''Fill Add tab form'''
        self.selenium.find_element(*self._plus_button).click()
        self._wait_for_results_refresh()
        time.sleep(5)
        self.selenium.find_element(*self._add_tab_button).click()
        self._wait_for_results_refresh()
        self.selenium.find_element(*self._tab_label).send_keys(tab_label)
        self.selenium.find_element(*self._tab_desc).send_keys(tab_desc)
        return Customization(self.testsetup)

    def add_box_to_dialog(self, box_label, box_desc):
        '''Fill add box form'''
        time.sleep(5)
        self.selenium.find_element(*self._plus_button).click()
        self._wait_for_results_refresh()
        time.sleep(5)
        self.selenium.find_element(*self._add_box_button).click()
        self._wait_for_results_refresh()
        self.selenium.find_element(*self._box_label).send_keys(box_label)
        self.selenium.find_element(*self._box_desc).send_keys(box_desc)
        return Customization(self.testsetup)

    def add_element_to_dialog(self, ele_label, ele_name, ele_desc):
        '''Fill element form'''
        self.selenium.find_element(*self._plus_button).click()
        self._wait_for_results_refresh()
        self.selenium.find_element(*self._add_element_button).click()
        time.sleep(3)
        self.selenium.find_element(*self._ele_label).send_keys(ele_label)
        self.selenium.find_element(*self._ele_name).send_keys(ele_name)
        self.selenium.find_element(*self._ele_desc).send_keys(ele_desc)
        self.select_dropdown("Text Box", *self._choose_type)
        #self.selenium.find_element(*self._default_value_text_box).\
           #  send_keys("service name")
        return Customization(self.testsetup)
