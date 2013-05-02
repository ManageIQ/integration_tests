# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By

class VirtualIntelligence(Base):
    @property
    def submenus(self):
        return {"report": VirtualIntelligence.Reports
                }

    class Reports(Base):
        _page_title = 'CloudForms Management Engine: Reports'

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup, TreeAccordionItem)

        def click_on_import_export(self):
            self.accordion.accordion_by_name("Import/Export").click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.ImportExport(self.testsetup)

    class ImportExport(Reports):
        _reports_import_field = (By.ID, "upload_file")
        _upload_button = (By.ID, "upload_atags")
        _overwrite_checkbox = (By.ID, "overwrite")

        @property
        def upload(self):
            return self.selenium.find_element(*self._upload_button)
        
        def check_overwrite_box(self):
            if not self.selenium.find_element(*self._overwrite_checkbox).is_selected():
                self.selenium.find_element(*self._overwrite_checkbox).click()

        def click_on_upload(self):
            self.upload.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Reports(self.testsetup)

        def import_reports(self, import_reports_file, overwrite = True):
            self._wait_for_results_refresh()
            if overwrite:
                self.check_overwrite_box()
            self.selenium.find_element(*self._reports_import_field).send_keys(import_reports_file)
            return self.click_on_upload()
