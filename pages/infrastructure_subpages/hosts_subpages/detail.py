# -*- coding: utf-8 -*-

from pages.base import Base
from pages.infrastructure_subpages.hosts_subpages.edit import Edit
from pages.regions.policy_menu import PolicyMenu
from pages.regions.taskbar.taskbar import TaskbarMixin
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


class Detail(Base, PolicyMenu, TaskbarMixin):
    _page_title = 'CloudForms Management Engine: Hosts'
    _host_detail_name_locator = (By.CSS_SELECTOR,
            'div#accordion > div > div > a')
    _details_locator = (By.CSS_SELECTOR, "div#textual_div")
    _edit_hosts_locator = (By.CSS_SELECTOR,
            "tr[title='Edit this Host']\
            >td.td_btn_txt>div.btn_sel_text")

    @property
    def edit_button(self):
        '''The edit button'''
        return self.selenium.find_element(
                *self._edit_hosts_locator)

    def click_on_edit_host(self):
        '''Click on edit host button'''
        ActionChains(self.selenium).click(
                self.configuration_button).click(
                        self.edit_button).perform()
        return Edit(self.testsetup)

    @property
    def details(self):
        from pages.regions.details import Details
        root_element = self.selenium.find_element(*self._details_locator)
        return Details(self.testsetup, root_element)

    @property
    def name(self):
        '''Name of host'''
        return self.selenium.find_element(
                *self._host_detail_name_locator).text.encode('utf-8')

    @property
    def hostname(self):
        '''Host hostname'''
        return self.details.get_section("Properties").get_item(
                "Hostname").value

    @property
    def ip_address(self):
        '''Host ip address'''
        return self.details.get_section("Properties").get_item(
                "IP Address").value

    @property
    def provider(self):
        '''Host parent provider name'''
        return self.details.get_section("Relationships").get_item(
                "Infrastructure Provider").value

    @property
    def cluster(self):
        '''Host parent cluster name'''
        return self.details.get_section("Relationships").get_item(
                "Cluster").value

    @property
    def datastores(self):
        '''Host parent datastore name'''
        return self.details.get_section("Relationships").get_item(
                "Datastores").value

    @property
    def vms(self):
        '''Number of VMs host is hosting'''
        return self.details.get_section("Relationships").get_item(
                "VMs").value
