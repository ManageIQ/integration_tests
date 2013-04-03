# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from pages.regions.paginator import PaginatorMixin

class Infrastructure(Base):
    @property
    def submenus(self):
        return {"management_system": lambda: Infrastructure.ManagementSystems,
                "pxe": lambda: Infrastructure.PXE
                }
        
    class ManagementSystems(Base, PaginatorMixin):
        _page_title = 'CloudForms Management Engine: Management Systems'
        _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
        _discover_management_systems_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Discover Management Systems']")

        @property
        def quadicon_region(self):
            from pages.regions.quadicons import Quadicons
            return Quadicons(self.testsetup, ["Configuration", "Policy"])
        
        @property
        def taskbar(self):
            from pages.regions.taskbar.taskbar import Taskbar
            return Taskbar(self.testsetup)
        
        def click_on_discover_management_systems(self):
            from selenium.webdriver.common.action_chains import ActionChains
            config_button = self.selenium.find_element(*self._configuration_button_locator)
            discover_button = self.selenium.find_element(*self._discover_management_systems_locator)
            ActionChains(self.selenium).click(config_button).click(discover_button).perform()
            return Infrastructure.ManagementSystemsDiscovery(self.testsetup)
    
    class ManagementSystemsDiscovery(Base):
        _page_title = 'CloudForms Management Engine: Management Systems'
        _start_button_locator = (By.CSS_SELECTOR, "input[name='start']")
        _cancel_button_locator = (By.CSS_SELECTOR, "input[name='cancel']")
        _management_system_type_locator = {
            "virtualcenter" : (By.CSS_SELECTOR, "input[name='discover_type_virtualcenter']"),
            "rhevm"         : (By.CSS_SELECTOR, "input[name='discover_type_rhevm']")
        }

        _from_first_locator = (By.CSS_SELECTOR, "input[name='from_first']")
        _from_second_locator = (By.CSS_SELECTOR, "input[name='from_second']")
        _from_third_locator = (By.CSS_SELECTOR, "input[name='from_third']")
        _from_fourth_locator = (By.CSS_SELECTOR, "input[name='from_fourth']")
        
        _to_fourth_locator = (By.CSS_SELECTOR, "input[name='to_fourth']")

        def is_selected(self, checkbox_locator):
            return self.selenium.find_element(*checkbox_locator).is_selected()
        
        def toggle_checkbox(self, checkbox_locator):
            self.selenium.find_element(*checkbox_locator).click()
        
        def mark_checkbox(self, checkbox_locator):
            if not self.is_selected(checkbox_locator):
                self.toggle_checkbox(checkbox_locator)
        
        def unmark_checkbox(self, checkbox_locator):
            if self.is_selected(checkbox_locator):
                self.toggle_checkbox(checkbox_locator)

        def click_on_start(self):
            self.selenium.find_element(*self._start_button_locator).click()
            return Infrastructure.ManagementSystems(self.testsetup)
        
        def click_on_cancel(self):
            self.selenium.find_element(*self._cancel_button_locator).click()
            return Infrastructure.ManagementSystems(self.testsetup)
        
        def discover_systems(self, management_system_type, from_address, to_address):
            self.mark_checkbox(self._management_system_type_locator[management_system_type])
            from_ip = from_address.split('.')
            to_ip = to_address.split('.')
            self.selenium.find_element(*self._from_first_locator).send_keys(from_ip[0])
            self.selenium.find_element(*self._from_second_locator).send_keys(from_ip[1])
            self.selenium.find_element(*self._from_third_locator).send_keys(from_ip[2])
            self.selenium.find_element(*self._from_fourth_locator).send_keys(from_ip[3])
            self.selenium.find_element(*self._to_fourth_locator).send_keys(to_ip[3])
            return self.click_on_start()
        
    class PXE(Base):
        _page_title = 'CloudForms Management Engine: PXE'
