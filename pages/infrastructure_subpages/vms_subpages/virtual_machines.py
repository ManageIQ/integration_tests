# -*- coding: utf-8 -*-
# pylint: disable=C0103
# pylint: disable=R0904

import re
from pages.regions.quadicons import Quadicons
from pages.regions.quadiconitem import QuadiconItem
from pages.infrastructure_subpages.vms_subpages.common import VmCommonComponents
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from utils.wait import wait_for
from utils.log import logger
import time


class VirtualMachines(VmCommonComponents):
    _provision_vms_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Request to Provision VMs']")
    _clone_items_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Clone this item']")
    _publish_items_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Publish selected VM to a Template']")
    _all_vms_button_locator = (By.CSS_SELECTOR,
        "a[title='All VMs & Templates that I can see']")

    @property
    def quadicon_region(self):
        return Quadicons(self.testsetup, VirtualMachines.VirtualMachineQuadIconItem)

    @property
    def search(self):
        from pages.regions.search import Search
        return Search(self.testsetup)

    def return_to_all_vms(self):
        """A function to return to the all vms page.

        As we use a single browser session, the "Virtual Machines" page can sometimes
        be left in a state where it is showing a VM and not a list of all VMs. This
        function attempts to return to the state of showing all VMs. However, this method
        can also be called whilst in a providers details page, in which case the
        button will not be present.
        """
        try:
            button = self.selenium.find_element(*self._all_vms_button_locator)
            button.click()
        except NoSuchElementException:
            pass

    def _mark_icon_and_call_method(self, vm_names, op_func):
        self.quadicon_region.mark_icon_checkbox(vm_names)
        op_func()

    def shutdown(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.shutdown)

    def shutdown_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.shutdown_and_cancel)

    def restart(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.restart)

    def restart_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.restart_and_cancel)

    def power_on(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.power_on)

    def power_on_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.power_on_and_cancel)

    def power_off(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.power_off)

    def power_off_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.power_off_and_cancel)

    def reset(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.reset)

    def reset_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.reset_and_cancel)

    def suspend(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.suspend)

    def suspend_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.power_button.suspend_and_cancel)

    def smart_state_scan(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.config_button.perform_smart_state_analysis)

    def smart_state_scan_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names,
            self.config_button.perform_smart_state_analysis_and_cancel)

    def refresh_relationships(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.config_button.refresh_relationships)

    def refresh_relationships_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names,
            self.config_button.refresh_relationships_and_cancel)

    def extract_running_processes(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.config_button.extract_running_processes)

    def extract_running_processes_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names,
            self.config_button.extract_running_processes_and_cancel)

        #def edit_vm(self,vm_name,click_cancel):
        #    self.quadicon_region.mark_icon_checkbox([vm_name])
        #    return Services.EditVm(self.testsetup, vm_name)

        #def set_ownership(self,vm_names,click_cancel):
        #    self.quadicon_region.mark_icon_checkbox(vm_names)
        #    return Services.SetOwnership(self.testsetup, vm_names)

    def remove_from_vmdb(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.config_button.remove_from_vmdb)

    def remove_from_vmdb_and_cancel(self, vm_names):
        self._mark_icon_and_call_method(vm_names, self.config_button.remove_from_vmdb_and_cancel)

    def click_on_provision_vms(self):
        provision_vms_button = self.get_element(*self._provision_vms_button_locator)
        ActionChains(self.selenium)\
            .click(self.center_buttons.lifecycle_button)\
            .click(provision_vms_button)\
            .perform()
        from pages.services_subpages.provision import ProvisionStart
        return ProvisionStart(self.testsetup)

    def click_on_clone_items(self, vm_name):
        self.find_vm_page(vm_name, None, True)
        clone_items_button = self.get_element(*self._clone_items_button_locator)
        ActionChains(self.selenium)\
            .click(self.center_buttons.lifecycle_button)\
            .click(clone_items_button)\
            .perform()
        from pages.services_subpages.provision import Provision
        return Provision(self.testsetup)

    def click_on_publish_items(self, vm_name):
        self.find_vm_page(vm_name, None, True)
        publish_items_button = self.get_element(*self._publish_items_button_locator)
        ActionChains(self.selenium)\
            .click(self.center_buttons.lifecycle_button)\
            .click(publish_items_button)\
            .perform()
        from pages.services_subpages.provision import Provision
        return Provision(self.testsetup)

    def find_vm_page(self, vm_name=None, vm_type=None, mark_checkbox=False,
            load_details=False, retries=0):
        self.return_to_all_vms()
        self._wait_for_results_refresh()
        if not self.view_buttons.is_grid_view:
            self.view_buttons.change_to_grid_view()
        logger.info(
            "Trying to find VM quadicon (" + str(vm_name) + ") and/or vm_type: " + str(vm_type))
        found = None
        retry_attempts = 0
        while not found:
            for quadicon in self.quadicon_region.quadicons:
                # find exact title/type match
                if quadicon.title == vm_name and \
                        quadicon.current_state == vm_type:
                    found = quadicon
                    logger.debug("Found VM quadicon (" + quadicon.title + ") with type: " + vm_type)
                    break
                # no title but first type
                elif vm_name is None and \
                        quadicon.current_state == vm_type:
                    found = quadicon
                    logger.debug("Found any VM quadicon with type: " + vm_type)
                    break
                # first title no type
                elif quadicon.title == vm_name and vm_type is None:
                    found = quadicon
                    logger.debug("Found VM quadicon (" + quadicon.title + ") with any type (" +
                        quadicon.current_state + ")")
                    break
                # if nothing found try turning the page
            if not found and not self.paginator.is_next_page_disabled:
                logger.debug("Matching VM not found, clicking next")
                self.paginator.click_next_page()
            elif not found and self.paginator.is_next_page_disabled and retry_attempts == retries:
                raise Exception(
                    "vm(" + str(vm_name) + ") with type(" + str(vm_type) + ") could not be found"
                )
            elif not found:
                logger.debug("Matching VM not found, moving to first page (retry: " +
                    str(retry_attempts) + " of " + str(retries) + ")")
                retry_attempts += 1
                time.sleep(30)
                self.paginator.click_first_page()
        if found and mark_checkbox:
            logger.debug("Matching VM found, marking checkbox")
            found.mark_checkbox()
        if found and load_details:
            logger.debug("Matching VM found, clicking on it to load details page")
            return found.click()

    def wait_for_vm_state_change(self, vm_quadicon_title, desired_state, timeout_in_minutes):
        """ Wait for VM to come to desired state.

        This function waits just the needed amount of time thanks to wait_for.

        Args:
            vm_quadicon_title:
                Displayed name of the VM
            desired_state:
                'on' or 'off'
            timeout_in_minutes:
                Specify amount of time to wait until TimedOutError is raised in minutes.

        Raises:
            TimedOutError:
                When VM does not come up to desired state in specified period of time.

        """
        def _check():
            self.refresh()
            self.find_vm_page(vm_quadicon_title, None, False)
            current_state = self.quadicon_region\
                .get_quadicon_by_title(vm_quadicon_title)\
                .current_state
            return current_state == desired_state

        return wait_for(_check, num_sec=timeout_in_minutes * 60)

    class VirtualMachineQuadIconItem(QuadiconItem):
        @property
        def os(self):
            image_src = self._root_element\
                .find_element(*self._quad_tl_locator)\
                .find_element_by_tag_name("img")\
                .get_attribute("src")
            return re.search('.+/os-(.+)\.png', image_src).group(1)

        @property
        def current_state(self):
            image_src = self._root_element\
                .find_element(*self._quad_tr_locator)\
                .find_element_by_tag_name("img")\
                .get_attribute("src")
            return re.search('.+/currentstate-(.+)\.png', image_src).group(1)

        @property
        def vendor(self):
            image_src = self._root_element\
                .find_element(*self._quad_bl_locator)\
                .find_element_by_tag_name("img")\
                .get_attribute("src")
            return re.search('.+/vendor-(.+)\.png', image_src).group(1)

        @property
        def snapshots(self):
            return self._root_element\
                .find_element(*self._quad_br_locator)\
                .text

        def click(self):
            self._root_element.click()
            self._wait_for_results_refresh()
            from pages.infrastructure_subpages.vms_subpages.details import VirtualMachineDetails
            return VirtualMachineDetails(self.testsetup)
