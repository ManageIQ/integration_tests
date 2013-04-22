# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

# TODO: write snmp trap receiver fixture to verify host shutdown/reboots

@pytest.fixture  # IGNORE:E1101
def vm_system():
    return 'pwr-ctl-vm-1-dnd'
    
@pytest.fixture  # IGNORE:E1101
def vm_pg(mozwebqa, home_page_logged_in, vm_system):
    vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
    Assert.true(vm_pg.is_the_current_page, "not on correct page")
    vm_pg.find_vm_page(vm_system,None,False)
    return vm_pg

@pytest.fixture  # IGNORE:E1101
# TODO: change this to use calls to the correct virt api to setup state
def verify_vm_running(vm_pg, vm_system):
    Assert.true(vm_pg.quadicon_region.does_quadicon_exist(vm_system), "vm not found")
    if vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state != 'on': 
        vm_pg.power_on([vm_system],False)
        vm_pg.wait_for_vm_state_change(vm_system, 'on', 10)
    return vm_pg

@pytest.fixture  # IGNORE:E1101
# TODO: change this to use calls to the correct virt api to setup state
def verify_vm_stopped(vm_pg, vm_system):
    Assert.true(vm_pg.quadicon_region.does_quadicon_exist(vm_system), "vm not found")
    if vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state != 'off':
        vm_pg.power_off([vm_system],False)
        vm_pg.wait_for_vm_state_change(vm_system, 'off', 10)
    return vm_pg


@pytest.mark.nondestructive  # IGNORE:E1101
class TestVmPowerControl:

    def test_vm_power_on(self, vm_system, verify_vm_stopped):
        vm_pg = verify_vm_stopped
        vm_pg.power_on([vm_system],False)
        Assert.true(vm_pg.flash.message.startswith("Start initiated"))
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
        Assert.true(vm_pg.flash.message.startswith("Stop initiated"))
        vm_pg.wait_for_vm_state_change(vm_system, 'off', 10)
        Assert.true(vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state == 'off', "vm running")

    def test_vm_power_off_cancel(self, vm_system, verify_vm_running):
        vm_pg = verify_vm_running
        vm_pg.power_off([vm_system],True)
        time.sleep(60)
        vm_pg.refresh() 
        vm_pg.find_vm_page(vm_system,None,False)
        Assert.true(vm_pg.quadicon_region.get_quadicon_by_title(vm_system).current_state == 'on', "vm not running")

@pytest.mark.nondestructive  # IGNORE:E1101
class TestVmDetailsPowerControl:

    def test_vm_power_on(self, vm_system, verify_vm_stopped):
        vm_pg = verify_vm_stopped
        vm_details = vm_pg.find_vm_page(vm_system,'off',False,True)
        Assert.true(vm_details.power_state == 'off', "power state pre-req wrong" )
        last_boot_time = vm_details.last_boot_time
        state_chg_time = vm_details.last_pwr_state_change
        vm_details.power_button.power_on(False)
        vm_details.wait_for_vm_state_change('on', 10)
        Assert.true(vm_details.power_state == 'on', "power state incorrect" )
        Assert.true(vm_details.last_boot_time != last_boot_time, "last boot time failed to update" )
        Assert.true(vm_details.last_pwr_state_change != state_chg_time, "last state chg time failed to update" )

    def test_vm_power_off(self, vm_system, verify_vm_running):
        vm_pg = verify_vm_running
        vm_details = vm_pg.find_vm_page(vm_system,'on',False,True)
        Assert.true(vm_details.power_state == 'on' , "power state pre-req wrong")
        last_boot_time = vm_details.last_boot_time
        state_chg_time = vm_details.last_pwr_state_change
        vm_details.power_button.power_off(False)
        vm_details.wait_for_vm_state_change('off', 10)
        Assert.true(vm_details.power_state == 'off', "power state incorrect" )
        Assert.true(vm_details.last_boot_time == last_boot_time, "last boot time failed to update" )
        Assert.true(vm_details.last_pwr_state_change != state_chg_time, "last state chg time failed to update" )

    #def test_vm_power_on_cancel(self,  vm_system, verify_vm_stopped):
    #def test_vm_power_off_cancel(self, vm_system, verify_vm_running):

