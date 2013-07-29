'''
Created on May 6, 2013

@author: bcrochet
'''
from pages.base import Base
from pages.services_subpages.provision import ProvisionFormButtonMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from pages.regions.list import ListRegion, ListItem

class ProvisionCustomize(Base, ProvisionFormButtonMixin):
    _customize_select_locator = (By.ID, "customize__sysprep_enabled")
    _root_password_field = (By.ID, "customize__root_password")
    _address_mode_dhcp = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td > input#customize__addr_mode[value='dhcp']")
    _address_mode_static = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td > input#customize__addr_mode[value='static']")
    _customization_template_list_locator = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td > div#prov_template_div > table > tbody")

    @property
    def customize(self):
        '''Basic Options - Customize

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._customize_select_locator))

    @property
    def root_password_field(self):
        return self.selenium.find_element(*self._root_password_field)

    @property
    def customization_template_list(self):
        return ListRegion(
            self.testsetup,
            self.get_element(*self._customization_template_list_locator),
                 ProvisionCustomize.CustomizationTemplateItem)

    def enter_root_password(self, root_password):
        self.root_password_field.send_keys(root_password)
        return ProvisionCustomize(self.testsetup)

    def select_address_mode(self, mode):
        if "static" in mode:
            self.selenium.find_element(*self._address_mode_static).click()
        elif "dhcp" in mode:
            self.selenium.find_element(*self._address_mode_dhcp).click()
        else:
            print "unknown mode"
        return ProvisionCustomize(self.testsetup)

    def select_customization_template(self, template_name):
        ct_items = self.customization_template_list.items
        selected_item = None
        for i in range(1, len(ct_items)):
            if ct_items[i].name == template_name:
                selected_item = ct_items[i]
                selected_item.click()
        self._wait_for_results_refresh()
        return ProvisionCustomize.CustomizationTemplateItem(selected_item)

    def fill_fields(self, root_password, mode, template_name):
        self.root_password_field.send_keys(root_password)
        self.select_address_mode(mode)
        self._wait_for_results_refresh()
        self.select_customization_template(template_name)
        return ProvisionCustomize(self.testsetup)

    class CustomizationTemplateItem(ListItem):
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
