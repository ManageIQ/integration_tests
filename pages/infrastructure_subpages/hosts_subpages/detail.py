# -*- coding: utf-8 -*-

from pages.base import Base
from pages.page import Page
from pages.infrastructure_subpages.hosts_subpages.edit import Edit
from pages.regions.accordion import Accordion
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
    _smartstate_analysis_locator = (By.CSS_SELECTOR,
            "tr[title='Perform SmartState Analysis on this Host']"
            ">td.td_btn_txt>div.btn_sel_text")

    @property
    def edit_button(self):
        '''The edit button'''
        return self.selenium.find_element(*self._edit_hosts_locator)

    def click_on_edit_host(self):
        '''Click on edit host button'''
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.edit_button)\
            .perform()
        return Edit(self.testsetup)

    @property
    def smartstate_analysis_button(self):
        '''The SmartState analysis button'''
        return self.selenium.find_element(*self._smartstate_analysis_locator)

    def click_on_smartstate_analysis_and_confirm(self):
        '''Click on SmartState analysis button and confirm popup'''
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.smartstate_analysis_button)\
            .perform()
        self.handle_popup()
        return Detail(self.testsetup)

    @property
    def details(self):
        from pages.regions.details import Details
        root_element = self.selenium.find_element(*self._details_locator)
        return Details(self.testsetup, root_element)

    @property
    def name(self):
        '''Name of host'''
        return self.selenium.find_element(*self._host_detail_name_locator).text.encode('utf-8')

    @property
    def hostname(self):
        '''Host hostname'''
        return self.details.get_section("Properties").get_item("Hostname").value

    @property
    def ip_address(self):
        '''Host ip address'''
        return self.details.get_section("Properties").get_item("IP Address").value

    @property
    def provider(self):
        '''Host parent provider name'''
        return self.details.get_section("Relationships").get_item("Infrastructure Provider").value

    @property
    def cluster(self):
        '''Host parent cluster name'''
        return self.details.get_section("Relationships").get_item("Cluster").value

    @property
    def datastores(self):
        '''Host parent datastore name'''
        return self.details.get_section("Relationships").get_item("Datastores").value

    @property
    def vms(self):
        '''Number of VMs host is hosting'''
        return self.details.get_section("Relationships").get_item("VMs").value

    @property
    def accordion_region(self):
        return Detail.HostAccordion(self.testsetup, Detail.HostAccordionItem)

    class HostAccordion(Accordion):
        '''Accordion specific to host detail page'''
        _accordion_locator = (By.CSS_SELECTOR, "div#accordion div.topbar")

    class HostAccordionItem(Page):
        '''Accordion item specific to host detail page'''
        _item_name_locator = (By.CSS_SELECTOR, "a")

        @property
        def _content_locator(self):
            '''Content is in the element next to the current, lookup using name of current'''
            return (
                By.XPATH,
                "//div[@class='topbar']/a[.='{}']/.."
                "/following-sibling::div[normalize-space()][1]".format(self.name)
            )

        @property
        def _active_link_locator(self):
            '''Only active links available (unpredictable HTML code structure in inactive links)'''
            return (By.XPATH, self._content_locator[1] + "/div//a[normalize-space()]")

        @property
        def name(self):
            return self._root_element.find_element(*self._item_name_locator).text

        @property
        def content(self):
            ''' Contains active and inactive links'''
            return self._root_element.find_element(*self._content_locator)

        @property
        def active_links(self):
            ''' Active links found in accordion item content'''
            return [Detail.HostAccordionItemLink(self.testsetup, element)
                for element in self.content.find_elements(*self._active_link_locator)]

        def active_link_by_name(self, text):
            for link in self.active_links:
                if text in link.name:
                    return link
            return None

        @property
        def is_expanded(self):
            if self.content.is_displayed():
                return True
            return False

        @property
        def is_collapsed(self):
            if not self.is_expanded:
                return True
            return False

        def click(self):
            wait_for_element = self._wait_for_visible_element
            if self.is_expanded:
                wait_for_element = self._wait_for_invisible_element

            self._root_element.find_element(*self._item_name_locator).click()
            wait_for_element(*self._content_locator)

    class HostAccordionItemLink(Page):
        '''Active link in accordion content'''

        @property
        def name(self):
            return self._root_element.text

        def click(self):
            self._root_element.click()
            self._wait_for_results_refresh()
