#!/usr/bin/env python

# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
from unittestzero import Assert

@pytest.fixture
def load_tasks(home_page_logged_in):
    ''' Fixture to navigate to the tasks page '''
    tasks_pg = home_page_logged_in.header.site_navigation_menu(
                        "Configuration").sub_navigation_menu("Tasks").click()
    return tasks_pg 

@pytest.mark.nondestructive
class TestTasks:

    def test_my_analysis_tab(self, load_tasks):
        ''' Test the my analysis tab components '''
        page = load_tasks.current_subtab.load_my_vm_analysis_tasks_tab()
        Assert.false(page.current_subtab.task_buttons.is_cancel_button_present)
        self.check_common_tab(page)
        page.filter_for_zone('<All Zones>')
        page.filter_for_task_state('Aborting')

    def test_my_other_tab(self, load_tasks):
        ''' Test the my other ui tasks tab components '''
        page = load_tasks.current_subtab.load_my_other_tasks_tab()
        Assert.false(page.current_subtab.task_buttons.is_cancel_button_present)
        self.check_common_tab(page)
        page.filter_for_task_state('Active')

    def test_all_analysis_tab(self, load_tasks):
        ''' Test the all vm analysis tab components '''
        page = load_tasks.current_subtab.load_all_vm_analysis_tasks_tab()
        Assert.true(page.current_subtab.task_buttons.is_cancel_button_present)
        self.check_common_tab(page)
        page.filter_for_zone('<All Zones>')
        page.filter_for_username('All Users')
        page.filter_for_task_state('Aborting')

    def test_all_other_tab(self, load_tasks):
        ''' Test the all other tasks tab components '''
        page = load_tasks.current_subtab.load_all_other_tasks_tab()
        Assert.true(page.current_subtab.task_buttons.is_cancel_button_present)
        self.check_common_tab(page)
        page.filter_for_username('All Users')
        page.filter_for_task_state('Active')

    def check_common_tab(self, page):
        ''' wrapper test for duplicate tests per tab '''
        page = page.task_buttons.reload()
        # requires tasks which may not be present
        #page.toggle_all_checkbox.uncheck()
        #Assert.false(page.toggle_all_checkbox.is_selected())
        #page.toggle_all_checkbox.check()
        #Assert.true(page.toggle_all_checkbox.is_selected())
        page.current_subtab.filter_for_queued_status.uncheck()
        Assert.false(page.current_subtab.filter_for_queued_status.is_selected())
        page.filter_for_running_status.uncheck()
        Assert.false(page.filter_for_running_status.is_selected())
        page.filter_for_ok_status.uncheck()
        Assert.false(page.filter_for_ok_status.is_selected())
        page.filter_for_error_status.uncheck()
        Assert.false(page.filter_for_error_status.is_selected())
        page.filter_for_warn_status.uncheck()
        Assert.false(page.filter_for_warn_status.is_selected())
        page.filter_for_queued_status.check()
        Assert.true(page.filter_for_queued_status.is_selected())
        page.filter_for_running_status.check()
        Assert.true(page.filter_for_running_status.is_selected())
        page.filter_for_ok_status.check()
        Assert.true(page.filter_for_ok_status.is_selected())
        page.filter_for_error_status.check()
        Assert.true(page.filter_for_error_status.is_selected())
        page.filter_for_warn_status.check()
        Assert.true(page.filter_for_warn_status.is_selected())
        Assert.true(page.task_buttons.is_delete_selected_option_disabled)
        Assert.true(page.task_buttons.is_delete_older_option_disabled)
        Assert.false(page.task_buttons.is_delete_all_option_disabled)
        page.filter_for_time_period('1 Day Ago')
        
