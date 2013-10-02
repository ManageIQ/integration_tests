# -*- coding: utf-8 -*-
import time
from pages.regions.quadicons import Quadicons
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.cloud.instances.common import CommonComponents


class Instances(CommonComponents):
    """Cloud Instances page"""

    _provision_instances_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Request to Provision Instances']")

    @property
    def quadicon_region(self):
        """The quadicon region"""
        from pages.cloud.instances.quadicon import InstanceQuadIcon
        return Quadicons(self.testsetup, InstanceQuadIcon)

    @property
    def search(self):
        """The search region"""
        from pages.regions.search import Search
        return Search(self.testsetup)

    def _mark_icon_and_call_method(self, instance_names, op_func):
        """Generic mark icon and call button action"""
        self.quadicon_region.mark_icon_checkbox(instance_names)
        op_func()

    def shutdown(self, instance_names):
        """Mark icon and shutdown"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.shutdown)

    def shutdown_and_cancel(self, instance_names):
        """Mark icon and shutdown but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.shutdown_and_cancel)

    def restart(self, instance_names):
        """Mark icon and restart"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.restart)

    def restart_and_cancel(self, instance_names):
        """Mark icon and restart but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.restart_and_cancel)

    def power_on(self, instance_names):
        """Mark icon and power on"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.power_on)

    def power_on_and_cancel(self, instance_names):
        """Mark icon and power on but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.power_on_and_cancel)

    def power_off(self, instance_names):
        """Mark icon and power off"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.power_off)

    def power_off_and_cancel(self, instance_names):
        """Mark icon and power off but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.power_off_and_cancel)

    def reset(self, instance_names):
        """Mark icon and reset"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.reset)

    def reset_and_cancel(self, instance_names):
        """Mark icon and reset but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.reset_and_cancel)

    def suspend(self, instance_names):
        """Mark icon and suspend"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.suspend)

    def suspend_and_cancel(self, instance_names):
        """Mark icon and suspend but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.power_button.suspend_and_cancel)

    def smart_state_scan(self, instance_names):
        """Mark icon and smart scan"""
        self._mark_icon_and_call_method(instance_names,
                self.config_button.perform_smart_state_analysis)

    def smart_state_scan_and_cancel(self, instance_names):
        """Mark icon and smart scan but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.config_button.perform_smart_state_analysis_and_cancel)

    def refresh_relationships(self, instance_names):
        """Mark icon and refresh relationships"""
        self._mark_icon_and_call_method(instance_names,
                self.config_button.refresh_relationships)

    def refresh_relationships_and_cancel(self, instance_names):
        """Mark icon and refresh relationships but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.config_button.refresh_relationships_and_cancel)

    def extract_running_processes(self, instance_names):
        """Mark icon and extract running processes"""
        self._mark_icon_and_call_method(instance_names,
                self.config_button.extract_running_processes)

    def extract_running_processes_and_cancel(self, instance_names):
        """Mark icon and extract running process but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.config_button.extract_running_processes_and_cancel)

        #def edit_vm(self,vm_name,click_cancel):
        #    self.quadicon_region.mark_icon_checkbox([vm_name])
        #    return Services.EditVm(self.testsetup, vm_name)

        #def set_ownership(self,instance_names,click_cancel):
        #    self.quadicon_region.mark_icon_checkbox(instance_names)
        #    return Services.SetOwnership(self.testsetup, instance_names)

    def remove_from_vmdb(self, instance_names):
        """Mark icon and remove from vmdb"""
        self._mark_icon_and_call_method(instance_names,
                self.config_button.remove_from_vmdb)

    def remove_from_vmdb_and_cancel(self, instance_names):
        """Mark icon and remove from vmdb but cancel request"""
        self._mark_icon_and_call_method(instance_names,
                self.config_button.remove_from_vmdb_and_cancel)

    def click_on_provision_instances(self):
        """Start instance provisioning """
        provision_instance_button = self.get_element(
            *self._provision_instances_button_locator)
        ActionChains(self.selenium).click(self.center_buttons.lifecycle_button)\
            .click(provision_instance_button).perform()
        from pages.services_subpages.provision import ProvisionStart
        return ProvisionStart(self.testsetup)

    def find_instance_page(self, instance_name=None, instance_type=None,
            mark_checkbox=False, load_details=False):
        """Page through any pages seaching for particular instance"""
        found = None
        while not found:
            for quadicon in self.quadicon_region.quadicons:
                # find exact title/type match
                if quadicon.title == instance_name and \
                        quadicon.current_state == instance_type:
                    found = quadicon
                    break
                # no title but first type
                elif instance_name is None and \
                        quadicon.current_state == instance_type:
                    found = quadicon
                    break
                # first title no type
                elif quadicon.title == instance_name and instance_type is None:
                    found = quadicon
                    break
                # if nothing found try turning the page
            if not found and not self.paginator.is_next_page_disabled:
                self.paginator.click_next_page()
            elif not found and self.paginator.is_next_page_disabled:
                errmsg = 'instance("%s") with type("%s") could not be found'
                raise Exception(errmsg % (instance_name, instance_type))
        if found and mark_checkbox:
            found.mark_checkbox()
        if found and load_details:
            return found.click()

    def wait_for_state_change(self, i_quadicon_title,
                desired_state, timeout_in_minutes, refresh=False):
        """Wait for instance to transition to particular state"""
        self.find_instance_page(i_quadicon_title, None, False)
        current_state = self.quadicon_region.get_quadicon_by_title(
            i_quadicon_title).current_state
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
                self.refresh_relationships([i_quadicon_title])
            time.sleep(60)
            minute_count += 1
            self.refresh()
            self.find_instance_page(i_quadicon_title, None, False)
            current_state = self.quadicon_region.get_quadicon_by_title(
                i_quadicon_title).current_state
            if minute_count == timeout_in_minutes and current_state != desired_state:
                raise Exception("timeout reached(" + str(timeout_in_minutes) +
                    " minutes) before desired state (" +
                    desired_state + ") reached... current state(" +
                    current_state + ")")
