'''
Created on May 31, 2013

@author: bcrochet
'''
from pages.base import Base
from pages.infrastructure_subpages.management_system_subpages.add import \
    ManagementSystemsAdd
from pages.infrastructure_subpages.management_system_subpages.detail import \
    ManagementSystemsDetail
from pages.infrastructure_subpages.management_system_subpages.discovery import \
    ManagementSystemsDiscovery
from pages.infrastructure_subpages.management_system_subpages.edit import \
    ManagementSystemsEdit
from pages.regions.paginator import PaginatorMixin
from pages.regions.policy_menu import PolicyMenu
from pages.regions.quadiconitem import QuadiconItem
from pages.regions.quadicons import Quadicons
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import re
import time


class ManagementSystems(Base, PaginatorMixin, PolicyMenu):
    _page_title = 'CloudForms Management Engine: Management Systems'
    _configuration_button_locator = (
            By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _discover_management_systems_locator = (
            By.CSS_SELECTOR,
            "table.buttons_cont tr[title='Discover Management Systems']")
    _edit_management_systems_locator = (
            By.CSS_SELECTOR,
            "table.buttons_cont tr[title='Select a single Management System to edit']")
    _remove_management_systems_locator = (
            By.CSS_SELECTOR,
            "table.buttons_cont tr[title='Remove selected Management Systems from the VMDB']")
    _add_new_management_system_locator = (
            By.CSS_SELECTOR,
            "table.buttons_cont tr[title='Add a New Management System']")

    @property
    def quadicon_region(self):
        return Quadicons(
                self.testsetup,
                self.ManagementSystemsQuadIconItem)

    @property
    def taskbar(self):
        from pages.regions.taskbar.taskbar import Taskbar
        return Taskbar(self.testsetup)

    @property
    def center_buttons(self):
        from pages.regions.taskbar.center import CenterButtons
        return CenterButtons(self.testsetup)

    @property
    def configuration_button(self):
        return self.selenium.find_element(
                *self._configuration_button_locator)

    @property
    def discover_button(self):
        return self.selenium.find_element(
                *self._discover_management_systems_locator)

    @property
    def edit_button(self):
        return self.selenium.find_element(
                *self._edit_management_systems_locator)

    @property
    def remove_button(self):
        return self.selenium.find_element(
                *self._remove_management_systems_locator)

    @property
    def add_button(self):
        return self.selenium.find_element(
                *self._add_new_management_system_locator)

    def select_management_system(self, management_system_name):
        self.quadicon_region.get_quadicon_by_title(
                management_system_name).mark_checkbox()

    def load_mgmt_system_details(self, management_system_name):
        self.quadicon_region.get_quadicon_by_title(management_system_name).click()
        self._wait_for_results_refresh()
        return ManagementSystemsDetail(self.testsetup)

    def wait_for_management_system_or_timeout(self,
            management_system_name,
            timeout=120):
        max_time = timeout
        wait_time = 1
        total_time = 0
        mgmt_sys = None
        while total_time <= max_time and mgmt_sys is not None:
            try:
                self.selenium.refresh()
                mgmt_sys = self.quadicon_region.get_quadicon_by_title(
                        management_system_name)
            except:
                total_time += wait_time
                time.sleep(wait_time)
                wait_time *= 2
                continue
        if mgmt_sys is None and total_time > max_time:
            raise Exception("Could not find management system in time")

    def click_on_discover_management_systems(self):
        ActionChains(self.selenium).click(
                self.configuration_button).click(
                        self.discover_button).perform()
        return ManagementSystemsDiscovery(self.testsetup)

    def click_on_edit_management_systems(self):
        ActionChains(self.selenium).click(
                self.configuration_button).click(
                        self.edit_button).perform()
        return ManagementSystemsEdit(self.testsetup)

    def click_on_remove_management_system(self):
        ActionChains(self.selenium).click(
                self.configuration_button).click(
                        self.remove_button).perform()
        self.handle_popup()
        return ManagementSystems(self.testsetup)

    def click_on_remove_management_system_and_cancel(self):
        ActionChains(self.selenium).click(
                self.configuration_button).click(
                        self.remove_button).perform()
        self.handle_popup(True)
        return ManagementSystems(self.testsetup)

    def click_on_add_new_management_system(self):
        ActionChains(self.selenium).click(
                self.configuration_button).click(self.add_button).perform()
        return ManagementSystemsAdd(self.testsetup)

    class ManagementSystemsQuadIconItem(QuadiconItem):
        @property
        def hypervisor_count(self):
            return self._root_element.find_element(
                    *self._quad_tl_locator).text

        # @property
        # def current_state(self):
        #    image_src = self._root_element.find_element(*self._quad_tr_locator).find_element_by_tag_name("img").get_attribute("src")
        #    return re.search('.+/currentstate-(.+)\.png',image_src).group(1)

        @property
        def vendor(self):
            image_src = self._root_element.find_element(
                    *self._quad_bl_locator).find_element_by_tag_name(
                            "img").get_attribute("src")
            return re.search('.+/vendor-(.+)\.png', image_src).group(1)

        @property
        def valid_credentials(self):
            image_src = self._root_element.find_element(
                    *self._quad_br_locator).find_element_by_tag_name(
                            "img").get_attribute("src")
            return 'checkmark' in image_src

        def click(self):
            self._root_element.click()
            self._wait_for_results_refresh()
            return ManagementSystemsDetail(self.testsetup)


