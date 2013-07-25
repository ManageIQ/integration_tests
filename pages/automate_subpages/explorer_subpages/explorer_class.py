# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.list import ListRegion, ListItem
from pages.regions.tabbuttonitem import TabButtonItem
from selenium.webdriver.support.select import Select
from time import sleep
from pages.automate_subpages.explorer_subpages.explorer_instance import ExplorerInstance
from pages.automate_subpages.explorer_subpages.explorer_method import ExplorerMethod
from pages.automate_subpages.explorer_subpages.explorer_property import ExplorerProperty
from pages.automate_subpages.explorer_subpages.explorer_schema import ExplorerSchema

class ClassFormButtonMixin(object):
    '''Mixin for shared buttons on the Class elements'''
    _template_form_buttons_locator = (
            By.CSS_SELECTOR,
            "div#form_buttons_div > table > tbody > tr > td > div")
    _template_save_button_locator = (
            By.CSS_SELECTOR,
            "li img[alt='Save']")
    _template_reset_button_locator = (
            By.CSS_SELECTOR,
            "li img[alt='Reset']")
    _template_cancel_button_locator = (
            By.CSS_SELECTOR,
            "li img[alt='Cancel']")

    @property
    def _form_buttons(self):
        '''Represents the set of form buttons.'''
        button_divs = self.selenium.find_elements(
                *self._template_form_buttons_locator)
        for div in button_divs:
            if "block" in div.value_of_css_property('display'):
                return div.find_element_by_css_selector("ul#form_buttons")
        return None

    @property
    def save_button(self):
        '''The save button. Will select the "visible" one'''
        return self._form_buttons.find_element(
                *self._template_save_button_locator)

    @property
    def reset_button(self):
        '''The reset button. Will select the "visible" one'''
        return self._form_buttons.find_element(
                *self._template_reset_button_locator)

    @property
    def cancel_button(self):
        '''The cancel button. Will select the "visible" one'''
        return self._form_buttons.find_element(
                *self._template_cancel_button_locator)


class ClassTabButtonItem(TabButtonItem):
    '''Specialization of TabButtonItem'''
    from pages.automate_subpages.explorer_subpages.explorer_instance import ExplorerInstance
    from pages.automate_subpages.explorer_subpages.explorer_method import ExplorerMethod
    from pages.automate_subpages.explorer_subpages.explorer_property import ExplorerProperty
    from pages.automate_subpages.explorer_subpages.explorer_schema import ExplorerSchema

    _item_page = {
                "Instances":  ExplorerInstance,
                "Methods":    ExplorerMethod,
                "Properties": ExplorerProperty,
                "Schema":     ExplorerSchema
            }


class ExplorerClass(Base):

    _name_class_field = (By.ID, "name")
    _display_name_class_field = (By.ID, "display_name")
    _description_class_field = (By.ID, "description")
    _inherits_from_select = (By.ID, "inherits_from")
    _add_system_button = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Add']")
    _configuration_button = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _tab_button_locator = (By.CSS_SELECTOR, "div#ae_tabs > ul > li")
    _instance_list_locator = (By.CSS_SELECTOR, "div#cls_inst_grid_div > div.objbox > table > tbody")

    # _methods
    _add_method_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a New Method']")

    # instances
    _add_instance_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a New Instance']")
    _edit_this_instance_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Select a single Instance to edit']")

    # properties
    _edit_this_class_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Edit this Class']")
    _remove_this_class_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Remove this Class']")

    #_schema
    _edit_schema_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Edit selected Schema']")

    _flash_message = (By.CSS_SELECTOR, "div#flash_text_div_class_instances > ul > li")


    @property
    def flash_message_class(self):
        return self.selenium.find_element(*self._flash_message).text

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button)

    @property
    def add_new_method_button(self):
        return self.selenium.find_element(*self._add_method_button)

    @property
    def add_new_instance_button(self):
        return self.selenium.find_element(*self._add_instance_button)

    @property
    def edit_this_instance_button(self):
        return self.selenium.find_element(*self._edit_this_instance_button)

    @property
    def edit_this_class_button(self):
        return self.selenium.find_element(*self._edit_this_class_button)

    @property
    def remove_this_class_button(self):
        return self.selenium.find_element(*self._remove_this_class_button)

    @property
    def edit_schema_button(self):
        return self.selenium.find_element(*self._edit_schema_button)

    @property
    def tabbutton_region(self):
        '''Return the tab button region'''
        from pages.regions.tabbuttons import TabButtons
        return TabButtons(self.testsetup,
                locator_override=self._tab_button_locator,
                cls=ClassTabButtonItem)

    def fill_class_info(self, class_name, class_display_name, class_description):
        self.selenium.find_element(*self._name_class_field).send_keys(class_name)
        self.selenium.find_element(*self._display_name_class_field).send_keys(class_display_name)
        self.selenium.find_element(*self._description_class_field).send_keys(class_description)
        self._wait_for_visible_element(*self._add_system_button)
        self.selenium.find_element(*self._add_system_button).click()
        self._wait_for_results_refresh()
        return ExplorerClass(self.testsetup)

    def click_on_add_new_instance(self):
        self._wait_for_results_refresh()
        ActionChains(self.selenium).click(self.configuration_button).click(self.add_new_instance_button).perform()
        self._wait_for_results_refresh()
        return ExplorerInstance(self.testsetup)

    def click_on_edit_this_instance(self):
        self._wait_for_results_refresh()
        ActionChains(self.selenium).click(self.configuration_button).click(self.edit_this_instance_button).perform()
        self._wait_for_results_refresh()
        return ExplorerInstance(self.testsetup)

    def click_on_add_new_method(self):
        self._wait_for_results_refresh()
        ActionChains(self.selenium).click(self.configuration_button).click(self.add_new_method_button).perform()
        self._wait_for_results_refresh()
        return ExplorerMethod(self.testsetup)

    def click_on_edit_this_class(self):
        self._wait_for_results_refresh()
        ActionChains(self.selenium).click(self.configuration_button).click(self.edit_this_class_button).perform()
        self._wait_for_results_refresh()
        return ExplorerClass(self.testsetup)

    def click_on_remove_this_class(self):
        self._wait_for_results_refresh()
        ActionChains(self.selenium).click(self.configuration_button).click(self.remove_this_class_button).perform()
        self.handle_popup(cancel=False)
        self._wait_for_results_refresh()
        from pages.automate import Automate
        return Automate.Explorer(self.testsetup)

    def click_on_edit_schema(self):
        self._wait_for_results_refresh()
        ActionChains(self.selenium).click(self.configuration_button).click(self.edit_schema_button).perform()
        self._wait_for_results_refresh()
        return ExplorerSchema(self.testsetup)

    def select_instance_item(self, item_name):
        instance_items = self.instance_list.items
        selected_item = None
        for i in range(1, len(instance_items)):
            if instance_items[i]._item_data[2].text == item_name:
                selected_item = instance_items[i]
                instance_items[i]._item_data[0].find_element_by_tag_name('img').click()
        self._wait_for_results_refresh()
        return ExplorerClass(self.testsetup)

    @property
    def instance_list(self):
        return ListRegion(
            self.testsetup,
            self.get_element(*self._instance_list_locator),
                 ExplorerClass.InstanceItem)

    class InstanceItem(ListItem):
        '''Represents an instance in the list'''
        _columns = ["checkbox", "folder", "name", "description"]

        @property
        def checkbox(self):
            pass

        @property
        def folder(self):
            pass

        @property
        def iname(self):
            return self._item_data[2].text

        @property
        def description(self):
            pass

