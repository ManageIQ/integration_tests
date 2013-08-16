# -*- coding: utf-8 -*-

import time
from pages.infrastructure_subpages.vms_subpages.common import VmCommonComponents
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.base import Base

class VirtualMachineDetails(VmCommonComponents):
    _details_locator = (By.CSS_SELECTOR, "div#textual_div")
    _set_retirement_date_button_locator = (By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Set Retirement Dates for this VM']")
    _immediately_retire_vm_button_locator = (By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Immediately Retire this VM']")
    _utilization_button_locator = (By.CSS_SELECTOR, 
        "table.buttons_cont tr[title="+
            "'Show Capacity & Utilization data for this VM']")
    _edit_mgmt_relationship_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/vm_evm_relationship.png']")
    _set_ownership_locator = (By.CSS_SELECTOR, "table.buttons_cont img[src='/images/toolbars/ownership.png']")

    @property
    def set_retirement_date_button(self):
        return self.selenium.find_element(
            *self._set_retirement_date_button_locator)

    @property
    def immediately_retire_vm_button(self):
        return self.selenium.find_element(
            *self._immediately_retire_vm_button_locator)

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
        from pages.regions.details import Details
        root_element = self.selenium.find_element(*self._details_locator)
        return Details(self.testsetup, root_element)

    def click_on_set_retirement_date(self):
        ActionChains(self.selenium).click(
            self.center_buttons.lifecycle_button).click(
                self.set_retirement_date_button).perform()
        self._wait_for_results_refresh()
        from pages.infrastructure_subpages.vms_subpages.retirement \
            import SetRetirementDate
        return SetRetirementDate(self.testsetup)

    def click_on_immediately_retire_vm(self, cancel=False):
        ActionChains(self.selenium).click(
            self.center_buttons.lifecycle_button).click(
                self.immediately_retire_vm_button).perform()
        self.handle_popup(cancel)
        self._wait_for_results_refresh()
        from pages.infrastructure_subpages.vms_subpages.virtual_machines \
            import VirtualMachines
        return VirtualMachines(self.testsetup)

    def click_on_utilization(self):
        ActionChains(self.selenium).click(
            self.center_buttons.monitoring_button).click(
                self.utilization_button).perform()
        self._wait_for_results_refresh()
        from pages.infrastructure_subpages.vms_subpages.utilization \
            import VirtualMachineUtil
        return VirtualMachineUtil(self.testsetup)

    def wait_for_vm_state_change(self, desired_state, timeout_in_minutes):
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
        '''Service method to edit cfme relationship and save from VM details'''
        edit_pg = self.click_on_edit_cfme_relationship()
        edit_pg.select_server(appliance_name)
        return edit_pg.click_on_save()

    def click_on_edit_cfme_relationship(self):
        '''Click on edit cfme relationship from center Configuration button'''
        ActionChains(self.selenium).click(
            self.center_buttons.configuration_button).click(self.server_relationship_button).perform()
        self._wait_for_results_refresh()
        return VirtualMachineDetails.EditCfmeRelationship(self.testsetup)

    def set_ownership_and_save(self, ownership):
        '''Service method to set template ownership and save from VM details'''
        edit_pg = self.click_on_set_ownership()
        edit_pg.select_user_ownership(ownership['user_owner'])
        edit_pg.select_group_ownership(ownership['group_owner'])
        return edit_pg.click_on_save()

    def click_on_set_ownership(self):
        '''Click on set ownership from center Configuration button'''
        ActionChains(self.selenium).click(
            self.center_buttons.configuration_button).click(self.set_ownership_button).perform()
        self._wait_for_results_refresh()
        return VirtualMachineDetails.SetOwnership(self.testsetup)

    class EditCfmeRelationship(Base):
        '''Edit CFME server relationship page'''
        _page_title = 'CloudForms Management Engine: Virtual Machines'
        _select_server_pulldown = (By.ID, "server_id")
        _save_button_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
        _cancel_button_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
        _reset_button_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

        def select_server(self, server_name):
            '''Select cfme server from dropdown menu'''
            self.select_dropdown(server_name, *self._select_server_pulldown)

        @property
        def save_button(self):
            '''Save button'''
            return self.get_element(*self._save_button_locator)

        @property
        def cancel_button(self):
            '''Cancel button'''
            return self.get_element(*self._cancel_button_locator)

        @property
        def reset_button(self):
            '''Reset button'''
            return self.get_element(*self._reset_button_locator)

        def click_on_save(self):
            '''Click on save button'''
            self._wait_for_visible_element(*self._save_button_locator)
            self.save_button.click()
            self._wait_for_results_refresh()
            return VirtualMachineDetails(self.testsetup)

        def click_on_cancel(self):
            '''Click on cancel button'''
            self.cancel_button.click()
            self._wait_for_results_refresh()
            return VirtualMachineDetails(self.testsetup)

        def click_on_reset(self):
            '''Click on reset button'''
            self._wait_for_visible_element(*self._reset_button_locator)
            self.reset_button.click()
            self._wait_for_results_refresh()
            return VirtualMachineDetails(self.testsetup)

    class SetOwnership(Base):
        '''Set Ownership for template'''
        _page_title = 'CloudForms Management Engine: Virtual Machines'
        _select_owner_pulldown = (By.ID, "user_name")
        _select_group_pulldown = (By.ID, "group_name")
        _save_button_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
        _cancel_button_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
        _reset_button_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

        def select_user_ownership(self, user_owner=None):
            '''Select a user as the template owner, if defined'''
            if user_owner is not None:
                self.select_dropdown(user_owner, *self._select_owner_pulldown)

        def select_group_ownership(self, group_owner=None):
            '''Select a user group as the template owner, if defined'''
            if group_owner is not None:
                self.select_dropdown(group_owner, *self._select_group_pulldown)

        @property
        def save_button(self):
            '''Save button'''
            return self.get_element(*self._save_button_locator)

        @property
        def cancel_button(self):
            '''Cancel button'''
            return self.get_element(*self._cancel_button_locator)

        @property
        def reset_button(self):
            '''Reset button'''
            return self.get_element(*self._reset_button_locator)

        def click_on_save(self):
            '''Click on save button'''
            self._wait_for_visible_element(*self._save_button_locator)
            self.save_button.click()
            self._wait_for_results_refresh()
            return VirtualMachineDetails(self.testsetup)

        def click_on_cancel(self):
            '''Click on cancel button'''
            self.cancel_button.click()
            self._wait_for_results_refresh()
            return VirtualMachineDetails(self.testsetup)

        def click_on_reset(self):
            '''Click on reset button'''
            self._wait_for_visible_element(*self._reset_button_locator)
            self.reset_button.click()
            self._wait_for_results_refresh()
            return VirtualMachineDetails(self.testsetup)
