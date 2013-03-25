# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from unittestzero import Assert

class PowerButton(Button):

    # Locators forced to use img src, different text dependent on All VMs vs specific VM details
    _power_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn img[src='/images/toolbars/power_choice.png']")
    _shutdown_option_locator = (By.CSS_SELECTOR, "table.buttons_cont img[src='/images/toolbars/guest_shutdown.png']")
    _restart_option_locator = (By.CSS_SELECTOR, "table.buttons_cont img[src='/images/toolbars/guest_restart.png']")
    _power_on_option_locator = (By.CSS_SELECTOR, "table.buttons_cont img[src='/images/toolbars/power_on.png']")
    _power_off_option_locator = (By.CSS_SELECTOR, "table.buttons_cont img[src='/images/toolbars/power_off.png']")
    _suspend_option_locator = (By.CSS_SELECTOR, "table.buttons_cont img[src='/images/toolbars/power_suspend.png']")
    _reset_option_locator = (By.CSS_SELECTOR, "table.buttons_cont img[src='/images/toolbars/power_reset.png']")
    
    def __init__(self,setup):
        Button.__init__(self,setup,*self._power_button_locator)
    
    def shutdown(self, cancel):
        item = self.selenium.find_element(*self._shutdown_option_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform() 
        self.handle_popup(cancel)

    def restart(self, cancel):
        item = self.selenium.find_element(*self._restart_option_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform() 
        self.handle_popup(self,cancel)

    def power_on(self, cancel):
        item = self.selenium.find_element(*self._power_on_option_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform() 
        self.handle_popup(cancel)

    def power_off(self, cancel):
        item = self.selenium.find_element(*self._power_off_option_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform() 
        self.handle_popup(cancel)

    def suspend(self, cancel):
        item = self.selenium.find_element(*self._suspend_option_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform() 
        self.handle_popup(cancel)

    def reset(self, cancel):
        item = self.selenium.find_element(*self._reset_option_locator)
        ActionChains(self.selenium).click(self._root_element).click(item).perform() 
        self.handle_popup(cancel)
