# -*- coding: utf-8 -*-

# pylint: disable=C0103
# pylint: disable=W0613
# pylint: disable=R0913
# pylint: disable=E1101

import random
import time
import pytest
from unittestzero import Assert
from utils.cfme_data import load_cfme_data
from utils.providers import infra_provider_type_map

# TODO: write snmp trap receiver fixture to verify host shutdown/reboots
# TODO: write event receiver

pytestmark = [pytest.mark.nondestructive,
              pytest.mark.usefixtures("setup_infrastructure_providers"),
              pytest.mark.usefixtures("maximized")]


def fetch_list(data):
    tests = []
    for provider in data["management_systems"]:
        prov_data = data['management_systems'][provider]
        if prov_data["type"] in infra_provider_type_map:
            if "test_vm_power_control" in prov_data:
                for vm_name in prov_data["test_vm_power_control"]:
                    tests.append(['', provider, vm_name])
    return tests


def pytest_generate_tests(metafunc):
    data = load_cfme_data(metafunc.config.option.cfme_data_filename)
    argnames = []
    tests = []

    if 'pwr_ctl_vms' in metafunc.fixturenames:
        argnames = ['pwr_ctl_vms', 'provider', 'vm_name']
        metafunc.parametrize(argnames, fetch_list(data), scope="module")
    elif 'random_pwr_ctl_vm' in metafunc.fixturenames:
        argnames = ['random_pwr_ctl_vm', 'provider', 'vm_name']
        all_tests = fetch_list(data)
        if all_tests:
            tests.append(random.choice(all_tests))
        metafunc.parametrize(argnames, tests, scope="module")

"""  These are in place for the reboot/reset/shutdown tests

def is_host_online(host):
    return 0 == call(["ping", "-c 1", host], stdout=PIPE)

def wait_for_host_to_go_offline(host, timeout_in_minutes):
    max_count = timeout_in_minutes * 4
    count = 0

    while (count < max_count):
        if ( not is_host_online(host) ):
            return True
        else:
            time.sleep(15)
            count += 1
    raise Exception("host never went offline in alloted time ("
            +str(timeout_in_minutes)+" minutes)")

def wait_for_host_to_come_online(host, timeout_in_minutes):
    max_count = timeout_in_minutes * 4
    count = 0

    while (count < max_count):
        if ( is_host_online(host) ):
            return True
        else:
            time.sleep(15)
            count += 1
    raise Exception("host came online in alloted time ("
            +str(timeout_in_minutes)+" minutes)")   """


@pytest.mark.usefixtures("random_pwr_ctl_vm")
class TestControlOnQuadicons():

    def test_power_off_cancel(
            self,
            load_providers_vm_list,
            provider,
            vm_name,
            verify_vm_running,
            mgmt_sys_api_clients):
        """Test the cancelling of a power off operation from the vm quadicon
        list.  Verify vm stays running"""
        vm_pg = load_providers_vm_list
        vm_pg.wait_for_vm_state_change(vm_name, 'on', 12)
        vm_pg.power_off_and_cancel([vm_name])
        time.sleep(45)
        vm_pg.refresh()
        vm_pg.find_vm_page(vm_name, None, False)
        Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(vm_name)
                .current_state, 'on', "vm not running")
        Assert.true(mgmt_sys_api_clients[provider].is_vm_running(vm_name),
                "vm not running")

    def test_power_off(
            self,
            load_providers_vm_list,
            provider,
            vm_name,
            verify_vm_running,
            mgmt_sys_api_clients):
        """Test power off operation on a single quadicon.  Verify vm
        transitions to stopped."""
        vm_pg = load_providers_vm_list
        vm_pg.wait_for_vm_state_change(vm_name, 'on', 12)
        vm_pg.power_off([vm_name])
        Assert.true(vm_pg.flash.message.startswith("Stop initiated"))
        vm_pg.wait_for_vm_state_change(vm_name, 'off', 12)
        Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(vm_name)
                .current_state, 'off', "vm running")
        Assert.true(mgmt_sys_api_clients[provider].is_vm_stopped(vm_name),
                "vm running")

    def test_power_on_cancel(
            self,
            load_providers_vm_list,
            provider,
            vm_name,
            verify_vm_stopped,
            mgmt_sys_api_clients):
        """Test the cancelling of a power on operation from the vm quadicon
        list.  Verify vm stays off."""
        vm_pg = load_providers_vm_list
        vm_pg.wait_for_vm_state_change(vm_name, 'off', 12)
        vm_pg.power_on_and_cancel([vm_name])
        time.sleep(45)
        vm_pg.refresh()
        vm_pg.find_vm_page(vm_name, None, False)
        Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(vm_name)
                .current_state, 'off', "vm running")
        Assert.true(mgmt_sys_api_clients[provider].is_vm_stopped(vm_name),
                "vm running")

    def test_power_on(
            self,
            load_providers_vm_list,
            provider,
            vm_name,
            verify_vm_stopped,
            mgmt_sys_api_clients):
        """Test power on operation for a single quadicon.  Verify vm
        transitions to running."""
        vm_pg = load_providers_vm_list
        vm_pg.wait_for_vm_state_change(vm_name, 'off', 12)
        vm_pg.power_on([vm_name])
        Assert.true(vm_pg.flash.message.startswith("Start initiated"))
        vm_pg.wait_for_vm_state_change(vm_name, 'on', 12)
        Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(vm_name)
                .current_state, 'on', "vm not running")
        Assert.true(mgmt_sys_api_clients[provider].is_vm_running(vm_name),
                "vm not running")


@pytest.mark.usefixtures("pwr_ctl_vms")
class TestVmDetailsPowerControlPerProvider:

    def test_vm_power_off(
            self,
            load_vm_details,
            provider,
            vm_name,
            verify_vm_running,
            mgmt_sys_api_clients):
        """Test power off operation from a vm details page. Verify vm
        transitions to stopped."""
        vm_details = load_vm_details
        vm_details.wait_for_vm_state_change('on', 12)
        last_boot_time = vm_details.last_boot_time
        state_chg_time = vm_details.last_pwr_state_change
        vm_details.power_button.power_off()
        vm_details.wait_for_vm_state_change('off', 12)
        Assert.equal(vm_details.power_state, 'off', "power state incorrect")
        Assert.equal(vm_details.last_boot_time, last_boot_time,
                "last boot time not updated")
        Assert.not_equal(vm_details.last_pwr_state_change, state_chg_time,
                "last state chg time failed to update")
        Assert.true(mgmt_sys_api_clients[provider].is_vm_stopped(vm_name),
                "vm running")

    def test_vm_power_on(
            self,
            load_vm_details,
            provider,
            vm_name,
            verify_vm_stopped,
            mgmt_sys_api_clients):
        """Test power on operation from a vm details page.  Verify vm
        transitions to running."""
        vm_details = load_vm_details
        vm_details.wait_for_vm_state_change('off', 12)
        last_boot_time = vm_details.last_boot_time
        state_chg_time = vm_details.last_pwr_state_change
        vm_details.power_button.power_on()
        vm_details.wait_for_vm_state_change('on', 12)
        Assert.equal(vm_details.power_state, 'on', "power state incorrect")
        self._wait_for_last_boot_timestamp_refresh(
            vm_details,
            last_boot_time,
            timeout_in_minutes=5)
        Assert.not_equal(vm_details.last_boot_time, last_boot_time,
                "last boot time failed to update")
        Assert.not_equal(vm_details.last_pwr_state_change, state_chg_time,
                "last state chg time failed to update")
        Assert.true(mgmt_sys_api_clients[provider].is_vm_running(vm_name),
                "vm not running")

    # this will fail on rhev without clicking refresh relationships, seems like
    # a event is not sent when rhev finishes saving state
    def test_suspend(
            self,
            load_vm_details,
            provider,
            vm_name,
            verify_vm_running,
            mgmt_sys_api_clients):
        """ Test suspend operation from a vm details page.  Verify vm
        transitions to suspended. """
        vm_details = load_vm_details
        vm_details.wait_for_vm_state_change('on', 10)
        last_boot_time = vm_details.last_boot_time
        state_chg_time = vm_details.last_pwr_state_change
        vm_details.power_button.suspend()
        vm_details.wait_for_vm_state_change('suspended', 15)
        Assert.equal(vm_details.power_state, 'suspended',
                "power state incorrect")
        Assert.equal(vm_details.last_boot_time, last_boot_time,
                "last boot time updated")
        Assert.not_equal(vm_details.last_pwr_state_change, state_chg_time,
                "last state chg time failed to update")
        Assert.true(mgmt_sys_api_clients[provider].is_vm_suspended(vm_name),
                "vm not suspended")

    def _wait_for_last_boot_timestamp_refresh(
            self,
            vm_details,
            boot_time,
            timeout_in_minutes):
        """Timestamp update doesn't happen with state change so need a longer
        wait when expecting a last boot timestamp change"""
        minute_count = 0
        while (minute_count < timeout_in_minutes):
            if boot_time != vm_details.last_boot_time:
                break
            print "Sleeping 60 seconds, iteration " + str(minute_count + 1)\
                + " of " + str(timeout_in_minutes)\
                + ", still no timestamp change"
            time.sleep(60)
            minute_count += 1
            vm_details.refresh()

    def test_start_from_suspend(
            self,
            load_vm_details,
            provider,
            vm_name,
            verify_vm_suspended,
            mgmt_sys_api_clients):
        """Test power_on operation on a suspended vm.

        Verify vm transitions to running."""

        vm_details = load_vm_details
        vm_details.wait_for_vm_state_change('suspended', 10)
        last_boot_time = vm_details.last_boot_time
        state_chg_time = vm_details.last_pwr_state_change
        vm_details.power_button.power_on()
        vm_details.wait_for_vm_state_change('on', 15)
        Assert.equal(vm_details.power_state, 'on', "power state incorrect")
        self._wait_for_last_boot_timestamp_refresh(
            vm_details,
            last_boot_time,
            timeout_in_minutes=5)
        Assert.not_equal(vm_details.last_boot_time, last_boot_time,
                "last boot time updated")
        Assert.not_equal(vm_details.last_pwr_state_change, state_chg_time,
                "last state chg time failed to update")
        Assert.true(mgmt_sys_api_clients[provider].is_vm_running(vm_name),
                "vm not running")

    # TODO: def test_guest_reboot(self, provider, vm_name):
    #    pass

    # TODO: def test_guest_shutdown(self, provider, vm_name):
    #    pass

    # TODO: def test_reset(self, provider, vm_name):
    #    pass


""" # TODO:
class TestMiscPowerControl:
    def test_no_power_control_on_templates

    def test_power_off_multiple_quadicon_vms

TESTS: add checks around options, when off, off shouldn't be listed, etc.
       when vm is ec2, no suspend button    """
