# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
from unittestzero import Assert

@pytest.fixture
def pick_random_vm(infra_vms_pg):
    return infra_vms_pg.find_vm_page(None, 'on', False, True)

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestVirtualMachines:
    @pytest.mark.nondestructive
    def test_vm_details(self, pick_random_vm):
        vm_details = pick_random_vm
        Assert.true(vm_details.details.does_info_section_exist('Properties'))
        Assert.not_none(vm_details.details.get_section(
                'Properties').get_item('Name'))

    @pytest.mark.nondestructive
    def test_vm_refresh_relationship(self, pick_random_vm):
        vm_details = pick_random_vm
        vm_details.config_button.refresh_relationships()
        Assert.true(vm_details.flash.message.startswith(
                'Refresh Ems initiated'))

    def test_set_vm_retirement_date(self, pick_random_vm):
        infra_vms_pg = pick_random_vm
        set_retirement_date_pg = infra_vms_pg.click_on_set_retirement_date()
        retirement_date = '7/30/2013'
        retirement_warning = '1 Week before retirement'
        set_retirement_date_pg.fill_data(retirement_date, retirement_warning)
        Assert.equal(set_retirement_date_pg.date_field.get_attribute(
                'value'), retirement_date)
        infra_vms_pg = set_retirement_date_pg.click_on_cancel()
        Assert.true(infra_vms_pg.flash.message.startswith(
                'Set/remove retirement date was cancelled by the user'))

    def test_immediately_retire_vm(self, pick_random_vm):
        infra_vms_pg = pick_random_vm
        vm_name = infra_vms_pg.details.get_section("Properties").get_item(
                "Name").value
        infra_vms_pg.click_on_immediately_retire_vm(cancel=True)
        Assert.equal(infra_vms_pg.details.get_section("Properties").get_item(
                "Name").value, vm_name)

'''
    def test_vm_util(self, pick_random_vm):
        vm_details_pg = pick_random_vm
        util_pg = vm_details_pg.click_on_utilization()

        interval = "Daily"
        date = "06/19/2013"
        show = "2 Weeks"
        time_zone = ""
        compare_to = ""
        #assert 0
        util_pg.fill_data(interval, show, time_zone, compare_to, date)
        util_pg._wait_for_results_refresh()
        Assert.true(util_pg.date_field.get_attribute("value") == date)
'''
