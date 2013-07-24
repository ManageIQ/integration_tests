# -*- coding: utf-8 -*-

import time
from pages.infrastructure_subpages.vms_subpages.common import VmCommonComponents
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

class VirtualMachineDetails(VmCommonComponents):
    _details_locator = (By.CSS_SELECTOR, "div#textual_div")
    _set_retirement_date_button_locator = (By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Set Retirement Dates for this VM']")
    _immediately_retire_vm_button_locator = (By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Immediately Retire this VM']")
    _utilization_button_locator = (By.CSS_SELECTOR, 
        "table.buttons_cont tr[title="+
            "'Show Capacity & Utilization data for this VM']")

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


