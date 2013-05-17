# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

class Automate(Base):
    @property
    def submenus(self):
        return {"miq_ae_class"         : Automate.Explorer,
                "miq_ae_tools"         : Automate.Simulation,
                "miq_ae_customization" : Automate.Customization,
                "miq_ae_export"        : Automate.ImportExport,
                "miq_ae_logs"          : Automate.Log,
                "miq_request_ae"       : Automate.Requests
                }

    class ImportExport(Base):
        _page_title = 'CloudForms Management Engine: Automate'
        _upload_button = (By.ID, "upload_atags")
        _commit_button = (By.CSS_SELECTOR, "a[title='Commit Import']")
        _automate_import_field = (By.ID, "upload_datastore")
        _export_button = (By.CSS_SELECTOR, "a[title='Export all classes and instances']")
        _reset_button = (By.CSS_SELECTOR, "a[title='Reset all custom classes and instances to default']")

        @property
        def upload(self):
            return self.selenium.find_element(*self._upload_button)

        @property
        def commit(self):
            return self.selenium.find_element(*self._commit_button)

        @property
        def export(self):
            return self.selenium.find_element(*self._export_button)

        @property
        def reset(self):
            return self.selenium.find_element(*self._reset_button)

        def click_on_upload(self):
            self.upload.click()
            self._wait_for_results_refresh()
            return Automate.ImportExport(self.testsetup)

        def click_on_commit(self):
            self.commit.click()
            self._wait_for_results_refresh()
            return Automate.ImportExport(self.testsetup)

        def click_on_export(self):
            self.export.click()
            # use pytest arg --firefoxpref=str to supress browser prompt
            self._wait_for_results_refresh()
            return Automate.ImportExport(self.testsetup)

        def click_on_reset(self):
            self.reset.click()
            self.handle_popup()
            return

        def click_on_reset_and_wait(self):
            self.click_on_reset()
            # reset takes ~30 secs. prevent selenium timeout
            # imp_wait will return sooner if completed earlier
            self.selenium.implicitly_wait(60)
            return Automate.ImportExport(self.testsetup)

        def import_automate(self, import_automate_file):
            self.selenium.find_element(*self._automate_import_field).send_keys(import_automate_file)
            return self.click_on_upload()

        def export_automate(self):
            return self.click_on_export()

        def reset_automate(self):
            return self.click_on_reset_and_wait()

    class Explorer(Base):
        _page_title = 'CloudForms Management Engine: Automate'
        _ae_tree = (By.ID, "ae_tree")
        _configuration_button = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
        _add_namespace_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a New Namespace']")
        _name_text_field = (By.ID, "ns_name")
        _description_text_field = (By.ID, "ns_description")
        _add_system_button = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Add']")
        _flash_message_area = (By.ID, "flash_msg_div_ns_list")
        _add_class_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a New Class']")
        _name_class_field = (By.ID, "name")
        _display_name_class_field = (By.ID, "display_name")
        _description_class_field = (By.ID, "description")
        _schema_button = (By.ID, "ui-id-5")
        _edit_schema_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Edit selected Schema']")
        _add_new_field_schema_button = (By.CSS_SELECTOR, "fieldset > table > tbody > tr[title='Click to add a new field']")
        _methods_button = (By.ID, "ui-id-32")
        _add_method_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a New Method']")
        _name_method_field = (By.ID, "cls_method_name")
        _display_name_method_field = (By.ID, "cls_method_display_name")
        _location_method_choice = (By.ID, "cls_method_location")
        _methods_table_cell = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td[title='Methods']")
        _validate_button = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Validate']")

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup,TreeAccordionItem)

        @property
        def configuration_button(self):
            return self.selenium.find_element(*self._configuration_button)

        @property
        def add_namespace_button(self):
            return self.selenium.find_element(*self._add_namespace_button)

        @property
        def add_class_button(self):
            return self.selenium.find_element(*self._add_class_button)

        @property
        def add_method_button(self):
            return self.selenium.find_element(*self._add_method_button)

        @property
        def method_table_cell(self):
            return self.selenium.find_element(*self._methods_table_cell)

        @property
        def return_flash_message(self):
            return self.selenium.find_element(*self._flash_message_area).text

        def click_on_add_new_namespace(self):
            self._wait_for_results_refresh()
            ActionChains(self.selenium).click(self.configuration_button).click(self.add_namespace_button).perform()
            self._wait_for_results_refresh()
            return Automate.Explorer(self.testsetup)

        def click_on_add_new_class(self):
            self._wait_for_results_refresh()
            ActionChains(self.selenium).click(self.configuration_button).click(self.add_class_button).perform()
            self._wait_for_results_refresh()
            return Automate.Explorer(self.testsetup)

        def fill_namespace_info(self, namespace_name, namespace_description):
            self.selenium.find_element(*self._name_text_field).send_keys(namespace_name)
            self.selenium.find_element(*self._description_text_field).send_keys(namespace_description)
            self.selenium.find_element(*self._add_system_button).click()
            self._wait_for_results_refresh()
            return Automate.Explorer(self.testsetup)

        def fill_class_info(self, class_name, class_display_name, class_description):
            self.selenium.find_element(*self._name_class_field).send_keys(class_name)
            self.selenium.find_element(*self._display_name_class_field).send_keys(class_display_name)
            self.selenium.find_element(*self._description_class_field).send_keys(class_description)
            self.selenium.find_element(*self._add_system_button).click()
            self._wait_for_results_refresh()
            return Automate.Explorer(self.testsetup)

        def click_on_add_new_method(self):
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._methods_button).click()
            self._wait_for_results_refresh()
            ActionChains(self.selenium).click(self.configuration_button).click(self.add_method_button).perform()
            self._wait_for_results_refresh()
            return Automate.Explorer(self.testsetup)

        def fill_method_info(self, method_name, method_display_name, location_choice):
            #TODO: complete interactions
            self._wait_for_results_refresh()
            return Automate.Explorer(self.testsetup)

        def click_on_method_table_cell(self, cell):
            self._wait_for_results_refresh()
            self.selenium.find_element(cell.click())
            self._wait_for_results_refresh()
            return Automate.Explorer(self.testsetup)

        def click_on_edit_schema(self):
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._schema_button).click()
            self._wait_for_results_refresh()
            ActionChains(self.selenium).click(self.configuration_button).click(*self._edit_schema_button).perform()
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._add_new_field_schema_button).click()
            return Automate.Explorer(self.testsetup)
