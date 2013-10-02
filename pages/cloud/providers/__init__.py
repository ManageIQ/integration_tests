from pages.base import Base
from pages.regions.paginator import PaginatorMixin
from pages.regions.policy_menu import PolicyMenu
from pages.regions.quadicons import Quadicons
from pages.regions.taskbar.taskbar import TaskbarMixin
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import time


class Providers(Base, PaginatorMixin, PolicyMenu, TaskbarMixin):
    '''Main Cloud Providers page'''
    _page_title = 'CloudForms Management Engine: Cloud Providers'
    _configuration_button_locator = (By.CSS_SELECTOR,
        "div.dhx_toolbar_btn[title='Configuration']")
    _discover_providers_locator = (By.CSS_SELECTOR,
        "tr[title='Discover Cloud Providers']>td.td_btn_txt>div.btn_sel_text")
    _edit_providers_locator = (By.CSS_SELECTOR,
        "tr[title='Select a single Cloud Provider to edit']>td.td_btn_txt>div.btn_sel_text")
    _remove_providers_locator = (By.CSS_SELECTOR,
        "tr[title='Remove selected Cloud Providers from the VMDB']>td.td_btn_txt>div.btn_sel_text")
    _add_new_provider_locator = (By.CSS_SELECTOR,
        "tr[title='Add a New Cloud Provider']>td.td_btn_txt>div.btn_sel_text")

    @property
    def quadicon_region(self):
        '''The quadicon region'''
        from pages.cloud.providers.quadicon import CloudProviderQuadIcon
        return Quadicons(self.testsetup, CloudProviderQuadIcon)

    @property
    def discover_button(self):
        '''The discover button'''
        return self.selenium.find_element(*self._discover_providers_locator)

    @property
    def edit_button(self):
        '''The edit button'''
        return self.selenium.find_element(*self._edit_providers_locator)

    @property
    def remove_button(self):
        '''The remove button'''
        return self.selenium.find_element(*self._remove_providers_locator)

    @property
    def add_button(self):
        '''The add button'''
        return self.selenium.find_element(*self._add_new_provider_locator)

    def select_provider(self, provider_name):
        '''Select a provider given a name'''
        # Needs to be on the quadicon view first
        self.taskbar_region.view_buttons.change_to_grid_view()
        self.quadicon_region.get_quadicon_by_title(provider_name).mark_checkbox()

    def load_provider_details(self, provider_name):
        '''Get provider details page given a name'''
        # Needs to be on the quadicon view first
        self.taskbar_region.view_buttons.change_to_grid_view()
        self.quadicon_region.get_quadicon_by_title(provider_name).click()
        self._wait_for_results_refresh()
        from pages.cloud.providers.details import Detail
        return Detail(self.testsetup)

    def wait_for_provider_or_timeout(self,
            provider_name,
            timeout=120):
        '''Wait for a provider to become available or timeout trying'''
        max_time = timeout
        wait_time = 1
        total_time = 0
        mgmt_sys = None
        while total_time <= max_time and mgmt_sys is not None:
            try:
                self.selenium.refresh()
                mgmt_sys = self.quadicon_region.get_quadicon_by_title(provider_name)
            except:
                total_time += wait_time
                time.sleep(wait_time)
                wait_time *= 2
                continue
        if mgmt_sys is None and total_time > max_time:
            raise Exception("Could not find management system in time")

    def click_on_discover_providers(self):
        '''Click on discover cloud provider button'''
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.discover_button).perform()
        from pages.cloud.providers.discovery import Discovery
        return Discovery(self.testsetup)

    def click_on_edit_providers(self):
        '''Click on edit cloud providers button'''
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.edit_button).perform()
        from pages.cloud.providers.edit import Edit
        return Edit(self.testsetup)

    def click_on_remove_provider(self):
        '''Click on remove cloud provider button'''
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.remove_button).perform()
        self.handle_popup()
        return Providers(self.testsetup)

    def click_on_remove_provider_and_cancel(self):
        '''Click on remove provider and cancel via popup'''
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.remove_button).perform()
        self.handle_popup(True)
        return Providers(self.testsetup)

    def click_on_add_new_provider(self):
        '''Click on add new provider button'''
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.add_button).perform()
        from pages.cloud.providers.add import Add
        return Add(self.testsetup)
