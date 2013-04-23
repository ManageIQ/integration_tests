# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By

class Control(Base):
    @property
    def submenus(self):
        return {"miq_policy_export": Control.ImportExport
                }
        
    class ImportExport(Base):
        _page_title = 'CloudForms Management Engine: Control'
        _upload_button = (By.ID, "upload_atags")
        _commit_button = (By.CSS_SELECTOR, "a[title='Commit Import']")
        _policy_import_field = (By.ID, "upload_file")

        @property
        def upload(self):
            return self.selenium.find_element(*self._upload_button)
        
        @property
        def commit(self):
            return self.selenium.find_element(*self._commit_button)

        def click_on_upload(self):
            self.upload.click()
            self._wait_for_results_refresh()
            return Control.ImportExport(self.testsetup)

        def click_on_commit(self):
            self.commit.click()
            self._wait_for_results_refresh()
            return Control.ImportExport(self.testsetup)

        def import_policies(self, import_policy_file):
            self.selenium.find_element(*self._policy_import_field).send_keys(import_policy_file)
            return self.click_on_upload()

