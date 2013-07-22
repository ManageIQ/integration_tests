# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.list import ListRegion, ListItem
from selenium.webdriver.support.select import Select
from time import sleep
from pages.automate_subpages.customization import Customization
from pages.automate_subpages.explorer_subpages.explorer_namespace import ExplorerNamespace
from pages.automate_subpages.explorer_subpages.explorer_class import ExplorerClass

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
        _export_button = (By.CSS_SELECTOR,
                "a[title='Export all classes and instances']")
        _reset_button = (By.CSS_SELECTOR,
                "a[title='Reset all custom classes and instances to default']")

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
            self.selenium.find_element(*self._automate_import_field).send_keys(
                    import_automate_file)
            return self.click_on_upload()

        def export_automate(self):
            return self.click_on_export()

        def reset_automate(self):
            return self.click_on_reset_and_wait()

    class Explorer(Base):
        _page_title = 'CloudForms Management Engine: Automate'
        _ae_tree = (By.ID, "ae_tree")
        _configuration_button = (By.CSS_SELECTOR,
                "div.dhx_toolbar_btn[title='Configuration']")
        _add_namespace_button = (By.CSS_SELECTOR,
                "table.buttons_cont tr[title='Add a New Namespace']")
        _add_class_button = (By.CSS_SELECTOR,
                "table.buttons_cont tr[title='Add a New Class']")
        _flash_message_area = (By.ID, "flash_msg_div_ns_list")

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
            return Accordion(self.testsetup, LegacyTreeAccordionItem)

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
        def namespace_flash_message_text(self):
            return self.selenium.find_element(*self._flash_message_area).text

        def click_on_namespace_access_node(self, node_name):
            self.accordion.current_content.find_node_by_name(node_name).click()
            self._wait_for_results_refresh()
            return ExplorerNamespace(self.testsetup)

        def click_on_add_new_namespace(self):
            self._wait_for_results_refresh()
            ActionChains(self.selenium).click(self.configuration_button).click(self.add_namespace_button).perform()
            self._wait_for_results_refresh()
            return ExplorerNamespace(self.testsetup)

        def click_on_class_access_node(self, node_name):
            self.accordion.current_content.find_node_by_name(node_name).click()
            self._wait_for_results_refresh()
            return ExplorerClass(self.testsetup)

        def click_on_add_new_class(self):
            self._wait_for_results_refresh()
            ActionChains(self.selenium).click(self.configuration_button).click(self.add_class_button).perform()
            self._wait_for_results_refresh()
            return ExplorerClass(self.testsetup)

    class Customization(Base):
        _page_title = 'CloudForms Management Engine: Customization'

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            return Accordion(self.testsetup)

        def click_on_service_dialog_accordion(self):
            self.accordion.accordion_by_name('Service Dialog').click()
            self._wait_for_results_refresh()
            return Customization(self.testsetup)
