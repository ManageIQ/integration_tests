#!/usr/bin/env python

from selenium.webdriver.support.ui import WebDriverWait
from pages.page import Page
from selenium.webdriver.common.by import By

class MainNavigationRegion(Page):
    _nav_tab_virtual_intelligence_field_locator = (By.ID, "nav-v-intelligence-a")
    _nav_tab_services_field_locator             = (By.ID, "nav-vms-a")
    _nav_tab_infrastructure_field_locator       = (By.ID, "nav-infrastructure-a")
    _nav_tab_vdi_field_locator                  = (By.ID, "nav-vdi-a")
    _nav_tab_storage_field_locator              = (By.ID, "nav-smis_storage-a")
    _nav_tab_control_field_locator              = (By.ID, "nav-policies-a")
    _nav_tab_automate_field_locator             = (By.ID, "nav-automation-a")
    _nav_tab_optimize_field_locator             = (By.ID, "nav-optimize-a")

    def _get_element(self, element_tuple):
        return self.selenium.find_element(*element_tuple)

    @property
    def virtual_intelligence_tab(self):
        return self._get_element(self._nav_tab_virtual_intelligence_field_locator)

    @property
    def services_tab(self):
        return self._get_element(self._nav_tab_services_field_locator)

    @property
    def infrastructure_tab(self):
        return self._get_element(self._nav_tab_infrastructure_field_locator)

    @property
    def vdi_tab(self):
        return self._get_element(self._nav_tab_vdi_field_locator)

    @property
    def storage_tab(self):
        return self._get_element(self._nav_tab_storage_field_locator)

    @property
    def control_tab(self):
        return self._get_element(self._nav_tab_control_field_locator)

    @property
    def automate_tab(self):
        return self._get_element(self._nav_tab_automate_field_locator)

    @property
    def optimize_tab(self):
        return self._get_element(self._nav_tab_optimize_field_locator)


