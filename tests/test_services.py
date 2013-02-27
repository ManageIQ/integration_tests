# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
from pages.login_page import LoginPage

@pytest.mark.nondestructive
class TestServices:
    def test_virtual_machines(self, mozwebqa):
        login_pg = LoginPage(mozwebqa)
        login_pg.go_to_login_page()
        home_pg = login_pg.login()
        Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
        vm_pg = home_pg.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        Assert.true(vm_pg.is_the_current_page)
        vm_pg.paginator.click_next_page()
        for vm in vm_pg.quadicon_region.quadicons:
            print "Snapshots " + vm.snapshots
        vm_pg.paginator.click_last_page()
        time.sleep(2)
        vm_pg.paginator.click_prev_page()
        time.sleep(2)
        vm_pg.paginator.click_first_page()
        time.sleep(2)
