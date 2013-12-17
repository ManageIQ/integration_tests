# -*- coding: utf-8 -*-

from pages.base import Base
from pages.infrastructure_subpages.host_provision import HostProvisionFormButtonMixin
from selenium.webdriver.common.by import By
from pages.regions.list import ListRegion, ListItem


class HostProvisionCustomize(Base, HostProvisionFormButtonMixin):
    _customize_template_list_locator = (By.CSS_SELECTOR,
                                        "fieldset > table > tbody > tr > td > \
                                        div#prov_template_div > table > tbody")
    _customize_hostname_field_locator = (By.ID, "customize__hostname")
    _customize_ip_addr_field_locator = (By.ID, "customize__ip_addr")
    _customize_subnet_mask_field_locator = (By.ID, "customize__subnet_mask")
    _customize_gateway_field_locator = (By.ID, "customize__gateway")
    _customize_password_field_locator = (By.ID, "customize__root_password")
    _customize_dns_servers_field_locator = (By.ID, "customize__dns_servers")

    @property
    def hostname(self):
        return self.get_element(*self._customize_hostname_field_locator)

    @property
    def ip_addr(self):
        return self.get_element(*self._customize_ip_addr_field_locator)

    @property
    def subnet_mask(self):
        return self.get_element(*self._customize_subnet_mask_field_locator)

    @property
    def gateway(self):
        return self.get_element(*self._customize_gateway_field_locator)

    @property
    def root_password(self):
        return self.get_element(*self._customize_password_field_locator)

    @property
    def dns_servers(self):
        return self.get_element(*self._customize_dns_servers_field_locator)

    @property
    def customize_template_list(self):
        return ListRegion(
            self.testsetup,
            self.get_element(*self._customize_template_list_locator), HostProvisionCustomize
                .CustomizeTemplateItem)

    def select_customize_template(self, template_name):
        ct_items = self.customize_template_list.items
        selected_item = None
        for i in range(1, len(ct_items)):
            if ct_items[i].name == template_name:
                selected_item = ct_items[i]
                selected_item.click()
        self._wait_for_results_refresh()
        return HostProvisionCustomize.CustomizeTemplateItem(selected_item)

    def fill_fields(self, template_name, hostname, ip_addr, subnet_mask, gateway,
                    rootpw, dns_servers):
        self.hostname.send_keys(hostname)
        self.ip_addr.send_keys(ip_addr)
        self.subnet_mask.send_keys(subnet_mask)
        self.gateway.send_keys(gateway)
        self.root_password.send_keys(rootpw)
        self.dns_servers.send_keys(dns_servers)
        self.select_customize_template(template_name)
        self._wait_for_results_refresh()
        return HostProvisionCustomize(self.testsetup)

    class CustomizeTemplateItem(ListItem):
        '''Represents a customization template in the list'''
        _columns = ["name", "description", "last_updated"]

        @property
        def name(self):
            return self._item_data[0].text

        @property
        def description(self):
            return self._item_data[1].text

        @property
        def last_updated(self):
            return self._item_data[2].text
