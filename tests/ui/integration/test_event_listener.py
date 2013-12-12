#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time


@pytest.fixture(scope="module",  # IGNORE:E1101
                params=["rhevm32"])
def mgmt_sys(request, cfme_data):
    param = request.param
    return cfme_data['management_systems'][param]


@pytest.mark.usefixtures("maximized")  # IGNORE:E1101
class TestVmPowerEvents():
    '''Toggle power state of VM(s) listed in cfme_data.yaml under
       'test_vm_power_control' and verify event(s) passed through automate
       and into running event listener

       Listener is managed by fixture setup_api_listener
       Listener code is tests/common/listener.py
    '''

    def test_vm_power_on_ui(self, infra_vms_pg, mgmt_sys, register_event):
        '''Power on guest via UI
        '''
        for vm in mgmt_sys['test_vm_power_control']:
            infra_vms_pg.wait_for_vm_state_change(vm, 'off', 3)
            vm_pg = infra_vms_pg.find_vm_page(vm, 'off', True, True)
            register_event(mgmt_sys['type'], "vm", vm, ["vm_power_on_req", "vm_power_on"])
            vm_pg.power_button.power_on()
            time.sleep(10)  # To settle it down

    def test_vm_power_off_ui(self, infra_vms_pg, mgmt_sys, register_event):
        '''Power off guest via UI
        '''
        for vm in mgmt_sys['test_vm_power_control']:
            infra_vms_pg.wait_for_vm_state_change(vm, 'on', 3)
            vm_pg = infra_vms_pg.find_vm_page(vm, 'on', True, True)
            register_event(mgmt_sys['type'], "vm", vm, "vm_power_off")
            vm_pg.power_button.power_off()
            time.sleep(10)  # To settle it down
