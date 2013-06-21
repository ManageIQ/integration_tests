# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By
from unittestzero import Assert

class TasksButtons(Button):
    '''
    classdocs
    '''
    _tasks_buttons_locator = (By.CSS_SELECTOR, 'div#center_buttons_div')
    _reload_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn img[src='/images/toolbars/reload.png']")
    _delete_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn img[src='/images/toolbars/delete_group.png']")
    _cancel_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Cancel the selected task']")
    
    _delete_option_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Delete selected tasks from the VMDB']")
    _delete_older_option_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Delete tasks older than the selected task']")
    _delete_all_option_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Delete all finished tasks']")

    _tab_button_active_locator = (By.CSS_SELECTOR, 'li.active')

    def __init__(self,setup):
        Button.__init__(self, setup, *self._tasks_buttons_locator)

    @property
    def tabbutton_region(self):
        ''' Returns the task tabs button region '''
        from pages.regions.tabbuttons import TabButtons
        from pages.configuration_subpages.tasks_tabs import TaskTabButtonItem
        return TabButtons(
                self.testsetup,
                active_override=self._tab_button_active_locator,
                cls=TaskTabButtonItem)
        
    @property
    def reload_button(self):
        return self._root_element.find_element(*self._reload_button_locator)
    
    def reload(self):
        self.reload_button.click()
        self._wait_for_results_refresh()
        return self.tabbutton_region.current_tab

    @property
    def cancel_button(self):
        return self._root_element.find_element(*self._cancel_button_locator)

    @property
    def is_cancel_button_present(self):
        return self.is_element_present(*self._cancel_button_locator)

    @property
    def is_cancel_button_disabled(self):
        if self.is_cancel_button_present():
            return 'dis' in self.cancel_button.get_attribute('class')
        else:
            raise Exception('Cancel button not found')

    def cancel_selected_tasks():
        self.reload_button.click()
        self.handle_popup(click_cancel=False)

    def cancel_selected_tasks_and_cancel():
        self.reload_button.click()
        self.handle_popup(click_cancel=True)

    @property
    def delete_button(self):
        return self._root_element.find_element(*self._delete_button_locator)
    
    @property
    def is_delete_selected_option_disabled(self):
        self.delete_button.click()
        result = 'tr_btn_disabled' in self.selenium.find_element(*self._delete_option_locator).get_attribute('class')
        self.delete_button.click()
        return result

    @property
    def is_delete_older_option_disabled(self):
        self.delete_button.click()
        result = 'tr_btn_disabled' in self.selenium.find_element(*self._delete_older_option_locator).get_attribute('class')
        self.delete_button.click()
        return result

    @property
    def is_delete_all_option_disabled(self):
        self.delete_button.click()
        result = 'tr_btn_disabled' in self.selenium.find_element(*self._delete_all_option_locator).get_attribute('class')
        self.delete_button.click()
        return result

    def _delete(self, option_locator, click_cancel):
        item = self.selenium.find_element(option_locator)
        ActionChains(self.selenium).click(self.delete_button).click(item).perform()
        self.handle_popup(click_cancel)

    def delete_selected(self):
        self._delete(*self._delete_option_locator, click_cancel=False)
        
    def delete_selected_and_cancel(self):
        self._delete(*self._delete_option_locator, click_cancel=True)
        
    def delete_older(self):
        self._delete(*self._delete_older_option_locator, click_cancel=False)
        
    def delete_older_and_cancel(self):
        self._delete(*self._delete_older_option_locator, click_cancel=True)
        
    def delete_all(self):
        self._delete(*self._delete_all_option_locator, click_cancel=False)
        
    def delete_all_and_cancel(self):
        self._delete(*self._delete_all_option_locator, click_cancel=True)
        
