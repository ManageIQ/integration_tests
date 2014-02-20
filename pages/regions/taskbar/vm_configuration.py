# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains


class ConfigButton(Button):

    # Locators forced to use img src, different text dependent on All VMs vs specific VM details
    _config_button_locator = (By.CSS_SELECTOR,
        "div.dhx_toolbar_btn img[src='/images/toolbars/vmdb.png']")
    _refresh_relationships_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/refresh.png']")
    _smart_state_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/scan.png']")
    _smart_state_locator_disabled = (By.CSS_SELECTOR,
        "table.buttons_cont tr[class*='tr_btn_disabled'] img[src='/images/toolbars/scan.png']")
    _running_processes_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/vm_collect_running_processes.png']")
    _running_processes_locator_disabled = (By.CSS_SELECTOR,
        "table.buttons_cont tr[class*='tr_btn_disabled'] \
        img[src='/images/toolbars/vm_collect_running_processes.png']")
    _edit_vm_locator = (By.CSS_SELECTOR, "table.buttons_cont img[src='/images/toolbars/edit.png']")
    _edit_vm_locator_disabled = (By.CSS_SELECTOR,
        "table.buttons_cont tr[class*='tr_btn_disabled'] img[src='/images/toolbars/edit.png']")
    _set_ownership_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/ownership.png']")
    _vmdb_removal_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/remove.png']")
    _edit_mgmt_relationship_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/vm_evm_relationship.png']")
    _size_recommendations_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/right_size.png']")
    _size_recommendations_locator_disabled = (By.CSS_SELECTOR,
        "table.buttons_cont tr[class*='tr_btn_disabled'] \
        img[src='/images/toolbars/right_size.png']")
    _compare_items_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/compare.png']")
    _compare_items_locator_disabled = (By.CSS_SELECTOR,
        "table.buttons_cont tr[class*='tr_btn_disabled'] img[src='/images/toolbars/compare.png']")
    _reconfigure_selected_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/reconfigure.png']")

    def __init__(self, setup):
        Button.__init__(self, setup, *self._config_button_locator)

    #def does_item_exist(self, key, raise_exception = False):
    def _is_item_enabled(self, item):
        self._root_element.click()
        return self.is_element_visible(*item)

    def _click_item(self, item, click_cancel=False):
        self._root_element.click()
        self.get_element(*item).click()
        self.handle_popup(click_cancel)

    def is_refresh_relationships_enabled(self):
        return self._is_item_enabled(self._refresh_relationships_locator)

    def refresh_relationships(self):
        self._click_item(self._refresh_relationships_locator)
        self._wait_for_results_refresh()

    def refresh_relationships_and_cancel(self):
        self._click_item(self._refresh_relationships_locator, click_cancel=True)

    def is_smart_state_analysis_enabled(self):
        return self._is_item_enabled(self._smart_state_locator)

    def perform_smart_state_analysis(self):
        self._click_item(self._smart_state_locator)

    def perform_smart_state_analysis_and_cancel(self):
        self._click_item(self._smart_state_locator, click_cancel=True)

    def is_extract_running_processes_enabled(self):
        return self._is_item_enabled(self._running_processes_locator)

    def extract_running_processes(self):
        self._click_item(self._running_processes_locator)

    def extract_running_processes_and_cancel(self):
        self._click_item(self._running_processes_locator, click_cancel=True)

    #def edit_this_vm(self):
    #    item = self.selenium.find_element(*self._edit_vm_locator)
    #    ActionChains(self.selenium).click(self._root_element).click(item).perform()
    #    return Services.EditVm(self.testsetup)

    #def edit_this_vm_and_cancel(self):
    #    item = self.selenium.find_element(*self._edit_vm_locator)
    #    ActionChains(self.selenium).click(self._root_element).click(item).perform()
    #    #return Services.EditVm(self.testsetup)

    def set_ownership(self):
        item = self.selenium.find_element(*self._set_ownership_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform()
        from pages.infrastructure_subpages.vms_subpages.details \
            import VirtualMachineDetails
        return VirtualMachineDetails.SetOwnership(self.testsetup)

    def remove_from_vmdb(self):
        item = self.selenium.find_element(*self._vmdb_removal_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform()
        self.handle_popup(False)

    def remove_from_vmdb_and_cancel(self):
        item = self.selenium.find_element(*self._vmdb_removal_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform()
        self.handle_popup(True)

    def edit_mgmt_engine_relationship(self):
        item = self.selenium.find_element(*self._edit_mgmt_relationship_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform()
        from pages.infrastructure_subpages.vms_subpages.details \
            import VirtualMachineDetails
        return VirtualMachineDetails.EditCfmeRelationship(self.testsetup)

    #def right_sized_recommendations(self):
    #    item = self.selenium.find_element(*self._size_recommendations_locator)
    #    ActionChains(self.selenium).click(self._root_element).click(item).perform()
    #    return Services.RightSize(self.testsetup)

    #def right_sized_recommendations_and_cancel(self):
    #    item = self.selenium.find_element(*self._size_recommendations_locator)
    #    ActionChains(self.selenium).click(self._root_element).click(item).perform()
    #    return Services.RightSize(self.testsetup)

    #def compare_selected_items(self):
    #    item = self.selenium.find_element(*self._compare_items_locator)
    #    ActionChains(self.selenium).click(self._root_element).click(item).perform()

    #def compare_selected_items_and_cancel(self):
    #    item = self.selenium.find_element(*self._compare_items_locator)
    #    ActionChains(self.selenium).click(self._root_element).click(item).perform()

    #def reconfigure_selected_items(self):
    #    item = self.selenium.find_element(*self._reconfigure_items_locator)
    #    ActionChains(self.selenium).click(self._root_element).click(item).perform()
    #    return Services.ReconfigureVm(self.testsetup)

    #def reconfigure_selected_items_and_cancel(self):
    #    item = self.selenium.find_element(*self._reconfigure_items_locator)
    #    ActionChains(self.selenium).click(self._root_element).click(item).perform()
    #    return Services.ReconfigureVm(self.testsetup)
