# -*- coding: utf-8 -*-
# pylint: disable=R0904
# pylint: disable=C0103

import time
from pages.cloud.instances.common import CommonComponents
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

class Details(CommonComponents):
    _details_locator = (By.CSS_SELECTOR, "div#textual_div")
    _set_retirement_date_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Set Retirement Dates for this Instance']")
    _immediately_retire_instance_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Immediately Retire this Instance']")
    _utilization_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title="+
            "'Show Capacity & Utilization data for this Instance']")
    _edit_mgmt_relationship_locator = (By.CSS_SELECTOR,
        "table.buttons_cont " +
        "img[src='/images/toolbars/vm_evm_relationship.png']")
    _set_ownership_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/ownership.png']")

    @property
    def set_retirement_date_button(self):
        return self.selenium.find_element(
            *self._set_retirement_date_button_locator)

    @property
    def immediately_retire_instance_button(self):
        return self.selenium.find_element(
            *self._immediately_retire_instance_button_locator)

    @property
    def utilization_button(self):
        return self.selenium.find_element(*self._utilization_button_locator)

    @property
    def server_relationship_button(self):
        return self.selenium.find_element(*self._edit_mgmt_relationship_locator)

    @property
    def set_ownership_button(self):
        return self.selenium.find_element(*self._set_ownership_locator)

    @property
    def power_state(self):
        return self.details.get_section(
            'Power Management').get_item('Power State').value

    @property
    def last_boot_time(self):
        return self.details.get_section(
            'Power Management').get_item('Last Boot Time').value

    @property
    def last_pwr_state_change(self):
        return self.details.get_section(
            'Power Management').get_item('State Changed On').value

    @property
    def details(self):
        root_element = self.selenium.find_element(*self._details_locator)
        from pages.regions.details import Details
        return Details(self.testsetup, root_element)

    def click_on_set_retirement_date(self):
        ActionChains(self.selenium).click(
            self.center_buttons.lifecycle_button).click(
                self.set_retirement_date_button).perform()
        self._wait_for_results_refresh()
        from pages.cloud.instances.retirement import Retirement
        return Retirement(self.testsetup)

    def click_on_immediately_retire_instance(self, cancel=False):
        ActionChains(self.selenium).click(
            self.center_buttons.lifecycle_button).click(
                self.immediately_retire_instance_button).perform()
        self.handle_popup(cancel)
        self._wait_for_results_refresh()
        from pages.cloud.instances import Instances
        return Instances(self.testsetup)

    def click_on_utilization(self):
        ActionChains(self.selenium).click(
            self.center_buttons.monitoring_button).click(
                self.utilization_button).perform()
        self._wait_for_results_refresh()
        from pages.cloud.instances.utilization import Utilization
        return Utilization(self.testsetup)

    def wait_for_instance_state_change(self, desired_state, timeout_in_minutes,
            refresh=False):
        current_state = self.power_state
        print "Desired state: " + desired_state + \
            "    Current state: " + current_state
        minute_count = 0
        while (minute_count < timeout_in_minutes):
            if (current_state == desired_state):
                break
            print "Sleeping 60 seconds, iteration " + str(minute_count+1) + \
                " of " + str(timeout_in_minutes) + ", desired state (" + \
                desired_state+") != current state("+current_state+")"
            if refresh:
                self.click_on_refresh_relationships()
            time.sleep(60)
            minute_count += 1
            self.refresh()
            current_state = self.power_state
            if (minute_count==timeout_in_minutes) and \
                (current_state != desired_state):
                raise Exception("timeout reached("+str(timeout_in_minutes)+
                                " minutes) before desired state (" +
                                desired_state+") reached... current state("+
                                current_state+")")

    def edit_cfme_relationship_and_save(self, appliance_name):
        """Service method to edit cfme relationship and save 
        from Instance details"""
        edit_pg = self.click_on_edit_cfme_relationship()
        edit_pg.select_server(appliance_name)
        return edit_pg.click_on_save()

    def click_on_edit_cfme_relationship(self):
        """Click on edit cfme relationship from center Configuration button"""
        ActionChains(self.selenium).click(
            self.center_buttons.configuration_button).click(
            self.server_relationship_button).perform()
        self._wait_for_results_refresh()
        from pages.cloud.instances.cfme_relationship \
            import CfmeRelationship
        return CfmeRelationship(self.testsetup)

    def set_ownership_and_save(self, ownership):
        """Service method to set template ownership and save 
        from Instance details"""
        edit_pg = self.click_on_set_ownership()
        edit_pg.select_user_ownership(ownership['user_owner'])
        edit_pg.select_group_ownership(ownership['group_owner'])
        return edit_pg.click_on_save()

    def click_on_set_ownership(self):
        """Click on set ownership from center Configuration button"""
        ActionChains(self.selenium).click(
            self.center_buttons.configuration_button).click(
            self.set_ownership_button).perform()
        self._wait_for_results_refresh()
        from pages.cloud.instances.ownership import Ownership
        return Ownership(self.testsetup)

    def click_on_refresh_relationships(self):
        ActionChains(self.selenium).click(
            self.center_buttons.configuration_button).click(
            self.refresh_relationships).perform()
        self._wait_for_results_refresh()
