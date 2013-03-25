# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

# TODO: write snmp trap receiver fixture to verify host shutdown/reboots

@pytest.fixture
def vm_system():
    return 'pwr-ctl-vm-1-dnd'
    
@pytest.fixture
def vm_pg(mozwebqa, home_page_logged_in, vm_system):
    vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
    Assert.true(vm_pg.is_the_current_page, "not on correct page")
    vm_pg.find_vm_page(vm_system,None,False)
    return vm_pg

@pytest.fixture    # TODO: change this to use calls to the correct virt api to setup state
def verify_vm_running(vm_pg, vm_system):
    Assert.true(vm_pg.quadicon_region.does_quadicon_exist(vm_system), "vm not found")
    if vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state != 'on': 
        vm_pg.power_on([vm_system],False)
        vm_pg.wait_for_vm_state_change(vm_system, 'on', 10)
    return vm_pg

@pytest.fixture    # TODO: change this to use calls to the correct virt api to setup state
def verify_vm_stopped(vm_pg, vm_system):
    Assert.true(vm_pg.quadicon_region.does_quadicon_exist(vm_system), "vm not found")
    if vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state != 'off':
        vm_pg.power_off([vm_system],False)
        vm_pg.wait_for_vm_state_change(vm_system, 'off', 10)
    return vm_pg


@pytest.mark.nondestructive
class TestVmPowerControl:

    def test_vm_power_on(self, vm_system, verify_vm_stopped):
        vm_pg = verify_vm_stopped
        vm_pg.power_on([vm_system],False)
        vm_pg.wait_for_vm_state_change(vm_system, 'on', 10)
        Assert.true(vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state == 'on', "vm not running")
    
    def test_vm_power_on_cancel(self, vm_system, verify_vm_stopped):
        vm_pg = verify_vm_stopped
        vm_pg.power_on([vm_system],True)
        time.sleep(60)
        vm_pg.refresh() 
        vm_pg.find_vm_page(vm_system,None,False)
        Assert.true(vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state == 'off', "vm running")
    
    def test_vm_power_off(self, vm_system, verify_vm_running):
        vm_pg = verify_vm_running
        vm_pg.power_off([vm_system],False)
        vm_pg.wait_for_vm_state_change(vm_system, 'off', 10)
        Assert.true(vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state == 'off', "vm running")

    def test_vm_power_off_cancel(self, vm_system, verify_vm_running):
        vm_pg = verify_vm_running
        vm_pg.power_off([vm_system],True)
        time.sleep(60)
        vm_pg.refresh() 
        vm_pg.find_vm_page(vm_system,None,False)
        Assert.true(vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state == 'on', "vm not running")
