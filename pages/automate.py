# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By

class Automate(Base):
    @property
    def submenus(self):
        return {"miq_ae_tools": lambda: Automate.ImportExport
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
