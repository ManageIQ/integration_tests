'''
Created on Feb 28, 2013

@author: bcrochet
'''

import pytest
import time
from unittestzero import Assert


class TestTaskbar:        
    @pytest.mark.nondestructive
    def test_history_buttons(self, mozwebqa, home_page_logged_in):
        vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        history_buttons = vm_pg.taskbar.history_buttons
        history_buttons.refresh_button.click()
        time.sleep(5)
        
    @pytest.mark.nondestructive
    def test_view_buttons(self,mozwebqa, home_page_logged_in, maximized):
        '''Note the use of maximized here. Currently, if the browser is too narrow,
        the view buttons are obscured by the search box. The maximized figure just 
        maximizes the browser window.
        '''
        vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        view_buttons = vm_pg.taskbar.view_buttons
        Assert.true(view_buttons.is_grid_view, "Not default grid view")
        view_buttons.change_to_tile_view()
        Assert.true(view_buttons.is_tile_view, "Not tile view")
        time.sleep(5)
        view_buttons.change_to_list_view()
        Assert.true(view_buttons.is_list_view, "Not list view")
        time.sleep(5)
        view_buttons.change_to_grid_view()
        Assert.true(view_buttons.is_grid_view, "Not grid view")
        time.sleep(5)
        