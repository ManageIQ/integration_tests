'''
Created on Feb 28, 2013

@author: bcrochet
'''

import pytest
import time
from unittestzero import Assert


class TestTaskbar:
    @pytest.fixture
    def home_page_logged_in(self, mozwebqa):
        from pages.login_page import LoginPage
        login_pg = LoginPage(mozwebqa)
        login_pg.go_to_login_page()
        home_pg = login_pg.login()
        Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
        return home_pg
        
    @pytest.mark.nondestructive
    def test_history_buttons(self, mozwebqa, home_page_logged_in):
        vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        history_buttons = vm_pg.taskbar.history_buttons
        history_buttons.refresh_button.click()
        time.sleep(5)
        
    @pytest.mark.nondestructive
    def test_view_buttons(self,mozwebqa, home_page_logged_in):
        vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        view_buttons = vm_pg.taskbar.view_buttons
        view_buttons.tile_view_button.click()
        time.sleep(5)
        view_buttons.list_view_button.click()
        time.sleep(5)
        view_buttons.grid_view_button.click()
        time.sleep(5)
        