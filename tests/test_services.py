# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.fixture
def pick_random_vm(mozwebqa, home_page_logged_in):
    vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
    vm_details = vm_pg.find_vm_page(None,'on',False,True)
    return vm_details


@pytest.mark.nondestructive
class TestServices:
    def test_virtual_machines(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
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

    @pytest.mark.nondestructive
    def test_vm_details(self, pick_random_vm):
        vm_details = pick_random_vm
        Assert.true(vm_details.details.does_info_section_exist('Properties'))
        Assert.true(vm_details.details.get_section('Properties').get_item('Name') != None)

    @pytest.mark.nondestructive
    def test_vm_smart_state_scan(self, pick_random_vm):
        vm_details = pick_random_vm
        vm_details.config_button.refresh_relationships(False)
        Assert.true(vm_details.flash.message.startswith("Refresh Ems initiated"))
