# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from pages.regions.tabbuttonitem import TabButtonItem
from pages.regions.paginator import PaginatorMixin
from pages.regions.list import ListRegion, ListItem

class Tasks(Base):

    class GeneralTab(Base, PaginatorMixin): 

        _page_title = None
        _tab_button_active_locator = (By.CSS_SELECTOR, 'li.active')
        _master_toggle_checkbox = (By.CSS_SELECTOR, 'input#masterToggle')
        _no_records_div_locator = (By.CSS_SELECTOR, 'div#no_records_div')

        # filter locators
        _zone_select_locator = (By.CSS_SELECTOR, 'select#chosen_zone')
        _username_select_locator = (By.CSS_SELECTOR, 'select#user_choice')
        _time_period_locator = (By.CSS_SELECTOR, 'select#time_period')
        _state_choice_locator = (By.CSS_SELECTOR, 'select#state_choice')
        _status_queued_checkbox = (By.CSS_SELECTOR, 'input#queued')
        _status_running_checkbox = (By.CSS_SELECTOR, 'input#running')
        _status_ok_checkbox = (By.CSS_SELECTOR, 'input#ok')
        _status_error_checkbox = (By.CSS_SELECTOR, 'input#error')
        _status_warn_checkbox = (By.CSS_SELECTOR, 'input#warn')

        #filter buttons
        _apply_filter_locator = (By.CSS_SELECTOR, 'img[alt="Apply"]')
        _reset_filter_locator = (By.CSS_SELECTOR, 'img[alt="Reset"]')
        _default_filter_locator = (By.CSS_SELECTOR, 'img[alt="Default"]')

        @property
        def current_subtab(self):
            return self.tabbutton_region.current_tab

        @property
        def tabbutton_region(self):
            ''' Returns the task tabs button region '''
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(
                    self.testsetup,
                    active_override=self._tab_button_active_locator,
                    cls=TaskTabButtonItem)

        def load_my_vm_analysis_tasks_tab(self):
            ''' Click the My VM Analysis Tasks tab '''
            return self.tabbutton_region.tabbutton_by_name('My VM Analysis Tasks').click()
            #return Tasks.MyVmAnalysisTasks(self.testsetup)

        def load_my_other_tasks_tab(self):
            ''' Click the My Other UI Tasks tab '''
            return self.tabbutton_region.tabbutton_by_name('My Other UI Tasks').click()
            #return Tasks.MyOtherUiTasks(self.testsetup)

        def load_all_vm_analysis_tasks_tab(self):
            ''' Click the All VM Analysis Tasks '''
            return self.tabbutton_region.tabbutton_by_name('All VM Analysis Tasks').click()
            #return Tasks.AllVmAnalysisTasks(self.testsetup)

        def load_all_other_tasks_tab(self):
            ''' Click the All Other Tasks tab '''
            return self.tabbutton_region.tabbutton_by_name('All Other Tasks').click()
            #return Tasks.AllOtherTasks(self.testsetup)

        @property
        def task_buttons(self):
            ''' Returns the task buttons region '''
            from pages.regions.taskbar.tasks import TasksButtons
            return TasksButtons(self.testsetup)

        @property
        def task_list(self):
            '''Returns the task list region'''
            _tasks_list_locator = ( By.CSS_SELECTOR, 'div#records_div > table > tbody')
            return ListRegion(
                self.testsetup,
                self.get_element(*_tasks_list_locator),
                self.TaskItem)

        @property
        def do_records_exist(self):
            ''' Do any records exist on the tab '''
            style = self.selenium.find_element(*self._no_records_div_locator).get_attribute('style')
            return 'display:none' not in style

        @property
        def total_task_count(self):
            ''' Returns the total number of tasks available '''
            if self.do_records_exist:
                return int(self.paginator.position_total)
            else:
                return 0

        @property
        def toggle_all_checkbox(self):
            ''' Returns toggle all checkbox web element '''
            from pages.configuration_subpages.tasks_tabs import MyCheckbox
            return MyCheckbox(self.selenium.find_element(*self._master_toggle_checkbox))

        def is_task_item_present(self, user, task_name, started_date, started_hour, started_minute):
            '''determine if task item is present'''
            task_items = self.task_list.items
            ts_string = started_date + ' ' +  str(started_hour) + ':' + str(started_minute)
            for item in task_items:
                if ts_string in item.started and user == item.user and task_name == item.task_name:
                    return True
            return False

        @property
        def filter_for_queued_status(self):
            ''' Web element for toggling queued_status filter '''
            from pages.configuration_subpages.tasks_tabs import MyCheckbox
            return MyCheckbox(self.selenium.find_element(*self._status_queued_checkbox))

        @property
        def filter_for_running_status(self):
            ''' Web element for toggling running_status filter '''
            from pages.configuration_subpages.tasks_tabs import MyCheckbox
            return MyCheckbox(self.selenium.find_element(*self._status_running_checkbox))

        @property
        def filter_for_ok_status(self):
            ''' Web element for toggling ok_status filter '''
            from pages.configuration_subpages.tasks_tabs import MyCheckbox
            return MyCheckbox(self.selenium.find_element(*self._status_ok_checkbox))

        @property
        def filter_for_error_status(self):
            ''' Web element for toggling error_status filter '''
            from pages.configuration_subpages.tasks_tabs import MyCheckbox
            return MyCheckbox(self.selenium.find_element(*self._status_error_checkbox))

        @property
        def filter_for_warn_status(self):
            ''' Web element for toggling warn_status filter '''
            from pages.configuration_subpages.tasks_tabs import MyCheckbox
            return MyCheckbox(self.selenium.find_element(*self._status_warn_checkbox))

        def filter_for_time_period(self, time_period):
             ''' Method to set time period filter '''
             self.select_dropdown(time_period, *self._time_period_locator)

        def filter_for_task_state(self, task_state):
             ''' Method to set task state filter '''
             self.select_dropdown(task_state, *self._state_choice_locator)


        @property
        def apply_button(self):
            ''' Web element for apply filter button '''
            return self.selenium.find_element(*self._apply_filter_locator)

        @property
        def reset_button(self):
            ''' Web element for reset filter button '''
            return self.selenium.find_element(*self._reset_filter_locator)

        @property
        def default_button(self):
            ''' Web element for default filter button '''
            return self.selenium.find_element(*self._default_filter_locator)

        @property
        def is_apply_button_disabled(self):
            return 'dimmed' in self.selenium.find_element(*self.apply_button).get_attribute('class')

        @property
        def is_reset_button_disabled(self):
            return 'dimmed' in self.selenium.find_element(*self.reset_button).get_attribute('class')

        @property
        def is_default_button_disabled(self):
            return 'dimmed' in self.selenium.find_element(*self.default_button).get_attribute('class')

        def apply_filter(self):
            self.apply_button.click()

        def reset_filter(self):
            self.reset_button.click()

        def default_filter(self):
            self.default_button.click()
        

                
        class TaskItem(ListItem):
            
            '''Represents an item in the profile list'''
            _columns = ['checkbox', 'status', 'updated', 'started', 'state', 'message', 'task name', 'user']

            @property
            def checkbox(self):
                '''checkbox for task record'''
                from pages.configuration_subpages.tasks_tabs import MyCheckbox
                return MyCheckbox(self._item_data[0])

            @property
            def status(self):
                '''status icon translation for task record'''
                image_src =  self._item_data[1].find_element_by_tag_name('img').get_attribute('src')
                stripped = re.search('.+/(.+)\.png', image_src).group(1)
                return stripped

            @property
            def updated(self):
                '''state field for task record'''
                return self._item_data[2].text.encode('utf-8')

            @property
            def started(self):
                '''state field for task record'''
                return self._item_data[3].text.encode('utf-8')

            @property
            def state(self):
                '''state field for task record'''
                return self._item_data[4].text.encode('utf-8')

            @property
            def message(self):
                '''message field for task record'''
                return self._item_data[5].text.encode('utf-8')

            @property
            def task_name(self):
                '''task name for task record'''
                return self._item_data[6].text.encode('utf-8')

            @property
            def user(self):
                '''user name for task record'''
                return self._item_data[7].text.encode('utf-8')

            @property
            def to_string(tself):
                '''string representation of task record'''
                return self.updated, self.started, self.state, self.message, self.task_name, self.user

            # TODO: fairly certain if its a vm task, you can click on it and go to vm details
            #def click(self):
            #    ''' click vm task record ''' 
            #    pass


    class MyVmAnalysisTasks(GeneralTab):
        _page_title = 'CloudForms Management Engine: My Tasks'

        def filter_for_zone(self, zone_name):
             self.select_dropdown(zone_name, *self._zone_select_locator)

    class MyOtherUiTasks(GeneralTab):
        _page_title = 'CloudForms Management Engine: My Ui Tasks'

    class AllVmAnalysisTasks(GeneralTab):
        _page_title = 'CloudForms Management Engine: All Tasks'

        def filter_for_username(self, username):
             self.select_dropdown(username, *self._username_select_locator)

        def filter_for_zone(self, zone_name):
             self.select_dropdown(zone_name, *self._zone_select_locator)

    class AllOtherTasks(GeneralTab):
        _page_title = 'CloudForms Management Engine: All UI Tasks'

        def filter_for_username(self, username):
             self.select_dropdown(username, *self._username_select_locator)

class MyCheckbox():

    def __init__(self,root_element):
        self._root_element = root_element

    def is_selected(self):
        return self._root_element.is_selected()

    def check(self):
        if self.is_selected():
            return True
        self._root_element.click()

    def uncheck(self):
        if not self.is_selected():
            return True
        self._root_element.click()

class TaskTabButtonItem(TabButtonItem):
    '''Specialization of TabButtonItem'''
    #import pytest
    #pytest.set_trace()

    _item_page = {
            'My VM Analysis Tasks': Tasks.MyVmAnalysisTasks,
            'My Other UI Tasks': Tasks.MyOtherUiTasks,
            'All VM Analysis Tasks': Tasks.AllVmAnalysisTasks,
            'All Other Tasks': Tasks.AllOtherTasks
    }

