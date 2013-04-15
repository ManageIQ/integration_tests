# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from pages.regions.paginator import PaginatorMixin
from selenium.webdriver.common.action_chains import ActionChains
import re

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
        _edit_management_systems_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Select a single Management System to edit']")

        @property
        def quadicon_region(self):
            from pages.regions.quadicons import Quadicons
            return Quadicons(self.testsetup)
        
        @property
        def taskbar(self):
            from pages.regions.taskbar.taskbar import Taskbar
            return Taskbar(self.testsetup)
        
        @property
        def configuration_button(self):
            return self.selenium.find_element(*self._configuration_button_locator)

        def select_management_system(self, management_system_name):
            self.quadicon_region.get_quadicon_by_title(management_system_name).mark_checkbox()

        def click_on_discover_management_systems(self):
            discover_button = self.selenium.find_element(*self._discover_management_systems_locator)
            ActionChains(self.selenium).click(self.configuration_button).click(discover_button).perform()
            return Infrastructure.ManagementSystemsDiscovery(self.testsetup)

        def click_on_edit_management_systems(self):
            edit_button = self.selenium.find_element(*self._edit_management_systems_locator)
            ActionChains(self.selenium).click(self.configuration_button).click(edit_button).perform()
            return Infrastructure.ManagementSystemsEdit(self.testsetup)

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

    class ManagementSystemsEdit(Base):
        _page_title = 'CloudForms Management Engine: Management Systems'
        _save_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Save Changes']")
        _cancel_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Cancel']")
        _name_edit_field_locator = (By.ID, "name")
        _hostname_edit_field_locator = (By.ID, "hostname")
        _ipaddress_edit_field_locator = (By.ID, "ipaddress")
        _server_zone_edit_field_locator = (By.ID, "server_zone")
        _host_default_vnc_port_start_edit_field_locator = (By.ID, "host_default_vnc_port_start")
        _host_default_vnc_port_end_edit_field_locator = (By.ID, "host_default_vnc_port_end")
        _default_userid_edit_field_locator = (By.ID, "default_userid")
        _default_password_edit_field_locator = (By.ID, "default_password")
        _default_verify_edit_field_locator = (By.ID, "default_verify")

        @property
        def name(self):
            return self.get_element(*self._name_edit_field_locator)

        @property
        def hostname(self):
            return self.get_element(*self._hostname_edit_field_locator)

        @property
        def ipaddress(self):
            return self.get_element(*self._ipaddress_edit_field_locator)

        @property
        def server_zone(self):
            return self.get_element(*self._server_zone_edit_field_locator)

        @property
        def host_default_vnc_port_start(self):
            return self.get_element(*self._host_default_vnc_port_start_edit_field_locator)

        @property
        def host_default_vnc_port_end(self):
            return self.get_element(*self._host_default_vnc_port_end_edit_field_locator)

        @property
        def default_userid(self):
            return self.get_element(*self._default_userid_edit_field_locator)

        @property
        def default_password(self):
            return self.get_element(*self._default_password_edit_field_locator)

        @property
        def default_verify(self):
            return self.get_element(*self._default_verify_edit_field_locator)

        def edit_management_system(self, management_system):
            for key,value in management_system.iteritems():
                # Special cases
                if "host_vnc_port" in key:
                    self.host_default_vnc_port_start.clear()
                    self.host_default_vnc_port_start.send_keys(value[0])
                    self.host_default_vnc_port_end.clear()
                    self.host_default_vnc_port_end.send_keys(value[1])
                elif "server_zone" in key:
                    from selenium.webdriver.support.select import Select
                    if self.server_zone.tag_name == "select":
                        select = Select(self.server_zone)
                        select.select_by_visible_text(value)
                elif "user" in key:
                    # use credentials
                    credentials = self.testsetup.credentials[value]
                    self.default_userid.clear()
                    self.default_userid.send_keys(credentials['username'])
                    self.default_password.clear()
                    self.default_password.send_keys(credentials['password'])
                    self.default_verify.clear()
                    self.default_verify.send_keys(credentials['password'])
                else:
                    # Only try to send keys if there is actually a property
                    if hasattr(self, key):
                        attr = getattr(self, key)
                        attr.clear()
                        attr.send_keys(value)
            return self.click_on_save()

        def click_on_save(self):
            self.get_element(*self._save_button_locator).click()
            self._wait_for_results_refresh()
            return Infrastructure.ManagementSystemsDetail(self.testsetup)

        def click_on_cancel(self):
            self.selenium.find_element(*self._cancel_button_locator).click()
            self._wait_for_results_refresh()
            return Infrastructure.ManagementSystems(self.testsetup)

    class ManagementSystemsDetail(Base):
        _page_title = 'CloudForms Management Engine: Management Systems'
        _management_system_detail_name_locator = (By.XPATH, '//*[@id="accordion"]/div[1]/div[1]/a')
        _management_system_detail_hostname_locator = (By.XPATH, '//*[@id="textual_div"]/dl/dd[1]/div[1]/table/tbody/tr[1]/td[2]')
        _management_system_detail_ip_address_locator = (By.XPATH, '//*[@id="textual_div"]/dl/dd[1]/div[1]/table/tbody/tr[2]/td[2]')
        _management_system_detail_zone_locator = (By.XPATH, '//*[@id="table_div"]/table/tbody/tr[1]/td[2]')
        _management_system_detail_credentials_validity_locator = (By.XPATH, '//*[@id="textual_div"]/dl/dd[1]/div[2]/table/tbody/tr/td[2]')
        _management_system_detail_vnc_port_range_locator = (By.XPATH, '//*[@id="textual_div"]/dl/dd[1]/div[1]/table/tbody/tr[9]/td[2]')

        @property
        def name(self):
            element_text = self.selenium.find_element(*self._management_system_detail_name_locator).text
            return re.search('.*(?=[ ]\(Summary\))', element_text).group(0)

        @property
        def hostname(self):
            return self.selenium.find_element(*self._management_system_detail_hostname_locator).text

        @property
        def zone(self):
            return self.selenium.find_element(*self._management_system_detail_zone_locator).text

        @property
        def credentials_validity(self):
            return self.selenium.find_element(*self._management_system_detail_credentials_validity_locator).text

        @property
        def vnc_port_range(self):
            element_text = self.selenium.find_element(*self._management_system_detail_vnc_port_range_locator).text
            return element_text.split('-')

        
    class PXE(Base):
        _page_title = 'CloudForms Management Engine: PXE'
