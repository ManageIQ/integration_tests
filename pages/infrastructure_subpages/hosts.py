# -*- coding: utf-8 -*-

from pages.base import Base
from pages.regions.policy_menu import PolicyMenu
from pages.regions.taskbar.taskbar import TaskbarMixin
from pages.regions.quadiconitem import QuadiconItem
from pages.regions.quadicons import Quadicons
import re
import time


class Hosts(Base, PolicyMenu, TaskbarMixin):
    _page_title = 'CloudForms Management Engine: Hosts'

    @property
    def quadicon_region(self):
        return Quadicons(
                self.testsetup, Hosts.HostQuadIconItem)

    @property
    def accordion_region(self):
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import TreeAccordionItem
        return Accordion(self.testsetup, TreeAccordionItem)

    def select_host(self, host_name):
        '''Mark host checkbox'''
        self.quadicon_region.get_quadicon_by_title(
                host_name).mark_checkbox()

    def click_host(self, host_name):
        '''Click on host'''
        from pages.infrastructure_subpages.hosts_subpages.detail \
            import Detail
        self.quadicon_region.get_quadicon_by_title(host_name).click()
        self._wait_for_results_refresh()
        return Detail(self.testsetup)

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
        max_time = timeout
        wait_time = 1
        total_time = 0
        host = None
        while total_time <= max_time and host is None:
            try:
                self.selenium.refresh()
                host = self.quadicon_region.get_quadicon_by_title(
                        host_name)
            except:
                total_time += wait_time
                time.sleep(wait_time)
                wait_time *= 2
        if total_time > max_time:
            raise Exception("Could not find host in time")

    @property
    def taskbar(self):
        from pages.regions.taskbar.taskbar import Taskbar
        return Taskbar(self.testsetup)

    class HostQuadIconItem(QuadiconItem):
        @property
        def vm_count(self):
            return self._root_element.find_element(
                    *self._quad_tl_locator).text

        @property
        def current_state(self):
            image_src = self._root_element.find_element(
                    *self._quad_tr_locator).find_element_by_tag_name(
                            "img").get_attribute("src")
            return re.search(r'.+/currentstate-(.+)\.png',
                    image_src).group(1)

        @property
        def vendor(self):
            '''Vendor name'''
            image_src = self._root_element.find_element(
                    *self._quad_bl_locator).find_element_by_tag_name(
                            "img").get_attribute("src")
            return re.search(r'.+/vendor-(.+)\.png', image_src).group(1)

        @property
        def valid_credentials(self):
            '''Status of credentials'''
            image_src = self._root_element.find_element(
                    *self._quad_br_locator).find_element_by_tag_name(
                            "img").get_attribute("src")
            return 'checkmark' in image_src

        def click(self):
            '''Click element'''
            from pages.infrastructure_subpages.hosts_subpages.detail \
                import Detail
            self._root_element.click()
            self._wait_for_results_refresh()
            return Detail(self.testsetup)
