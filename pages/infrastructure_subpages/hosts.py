# -*- coding: utf-8 -*-

from pages.base import Base
from pages.regions.policy_menu import PolicyMenu
from pages.regions.taskbar.taskbar import TaskbarMixin
from pages.regions.taskbar.power import CommonPowerButton
from pages.regions.quadiconitem import QuadiconItem
from pages.regions.quadicons import Quadicons
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from utils.wait import wait_for
import re


class Hosts(Base, PolicyMenu, TaskbarMixin, CommonPowerButton):
    _page_title = 'CloudForms Management Engine: Hosts'
    _configuration_button_locator = (By.CSS_SELECTOR,
            "div.dhx_toolbar_btn[title='Configuration']")
    _add_new_host_locator = (By.CSS_SELECTOR,
        "tr[title='Add a New Host']\
        >td.td_btn_txt>div.btn_sel_text")
    _remove_host_locator = (By.CSS_SELECTOR,
        "tr[title='Remove Selected Hosts from the VMDB']\
        >td.td_btn_txt>div.btn_sel_text")

    @property
    def quadicon_region(self):
        return Quadicons(self.testsetup, Hosts.HostQuadIconItem)

    @property
    def accordion_region(self):
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import TreeAccordionItem
        return Accordion(self.testsetup, TreeAccordionItem)

    @property
    def add_button(self):
        return self.selenium.find_element(*self._add_new_host_locator)

    @property
    def remove_button(self):
        return self.selenium.find_element(*self._remove_host_locator)

    def does_host_exist(self, host_name):
        try:
            self.quadicon_region.get_quadicon_by_title(host_name)
            return True
        except Exception:
            return False

    def reset_host(self, host_name):
        self.select_host(host_name)
        self.reset()
        self._wait_for_results_refresh()

    def power_on_host(self, host_name):
        self.select_host(host_name)
        self.power_on()
        self._wait_for_results_refresh()

    def power_off_host(self, host_name):
        self.select_host(host_name)
        self.power_off()
        self._wait_for_results_refresh()

    def check_host_and_refresh(self, host_name):
        if self.does_host_exist(host_name):
            return True
        self.selenium.refresh()
        return False

    def select_host(self, host_name):
        '''Mark host checkbox'''
        self.quadicon_region.get_quadicon_by_title(host_name).mark_checkbox()

    def click_host(self, host_name):
        '''Click on host'''
        from pages.infrastructure_subpages.hosts_subpages.detail \
            import Detail
        self.quadicon_region.get_quadicon_by_title(host_name).click()
        self._wait_for_results_refresh()
        return Detail(self.testsetup)

    def click_add_new_host(self):
        from pages.infrastructure_subpages.hosts_subpages.add import Add
        ActionChains(self.selenium).click(
            self.configuration_button).click(self.add_button).perform()
        return Add(self.testsetup)

    def click_remove_host(self):
        ActionChains(self.selenium).click(
            self.configuration_button).click(self.remove_button).perform()
        self.handle_popup()
        self._wait_for_results_refresh()
        return

    def edit_host_and_save(self, host):
        '''Service method to click on host, edit, fill with data and save

        host param is a dict of data to fill edit host form
        '''
        edit_host_pg = self.click_host(host['name']).click_on_edit_host()
        edit_host_pg.edit_host(host)
        return edit_host_pg.click_on_save()

    def edit_host_and_cancel(self, host):
        '''Service method to click on host, edit, fill with data and cancel

        host param is a dict of data to fill edit host form
        '''
        edit_host_pg = self.click_host(host['name']).click_on_edit_host()
        edit_host_pg.edit_host(host)
        return edit_host_pg.click_on_cancel()

    def wait_for_host_or_timeout(self, host_name, timeout=120):
        '''Wait for a host to become available or timeout trying'''
        wait_for(
            self.check_host_and_refresh,
            func_args=[host_name],
            num_sec=timeout,
            delay=2,
            expo=True)

    @property
    def taskbar(self):
        from pages.regions.taskbar.taskbar import Taskbar
        return Taskbar(self.testsetup)

    class HostQuadIconItem(QuadiconItem):
        @property
        def vm_count(self):
            return self._root_element.find_element(*self._quad_tl_locator).text

        @property
        def current_state(self):
            image_src = self._root_element.find_element(*self._quad_tr_locator) \
                                          .find_element_by_tag_name("img").get_attribute("src")
            return re.search(r'.+/currentstate-(.+)\.png',
                    image_src).group(1)

        @property
        def vendor(self):
            '''Vendor name'''
            image_src = self._root_element.find_element(*self._quad_bl_locator) \
                                          .find_element_by_tag_name("img").get_attribute("src")
            return re.search(r'.+/vendor-(.+)\.png', image_src).group(1)

        @property
        def valid_credentials(self):
            '''Status of credentials'''
            image_src = self._root_element.find_element(*self._quad_br_locator) \
                                          .find_element_by_tag_name("img").get_attribute("src")
            return 'checkmark' in image_src

        def click(self):
            '''Click element'''
            from pages.infrastructure_subpages.hosts_subpages.detail \
                import Detail
            self._root_element.click()
            self._wait_for_results_refresh()
            return Detail(self.testsetup)
