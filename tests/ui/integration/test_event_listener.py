#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
import re
import requests
import logging
import shutil


@pytest.fixture(scope="module",  # IGNORE:E1101
                params=["rhevm31"])
def mgmt_sys(request, cfme_data):
    param = request.param
    return cfme_data.data['management_systems'][param]


class APIMethods():
    '''Helper methods to read/write to running API listener
    '''
    def __init__(self, cfme_data):
        self.listener_host = cfme_data['listener']

    def _get(self, route):
        '''query event listener
        '''
        listener_url = "%s:%s" % (self.listener_host['url'], self.listener_host['port'])
        logging.info("checking api: %s%s" % (listener_url, route))
        r = requests.get(listener_url + route)
        r.raise_for_status()
        logging.debug("Response: %s" % r.json)
        return r.json

    def check_db(self, sys_type, obj_type, obj, event):
        '''Utility to check listener database for event
        '''
        max_attempts = 24
        sleep_interval = 10 
        req = "/events/%s/%s?event=%s" % (self.mgmt_sys_type(sys_type, obj_type), obj, event)
        for attempt in range(1, max_attempts+1):
            try:
                assert len(self._get(req)) == 1
            except AssertionError as e:
                if attempt < max_attempts:
                    logging.debug("Waiting for DB (%s/%s): %s" % (attempt, max_attempts, e))
                    time.sleep(sleep_interval)
                    pass
                # Enough sleeping, something went wrong
                else:
                    logging.exception("Check DB failed. Max attempts: '%s'." % (max_attempts))
                    raise e
            else:
                # No exceptions raised
                logging.info("DB row found for '%s'" % req)
                break

        return True

    def mgmt_sys_type(self, sys_type, obj_type):
        '''Map management system type from cfme_data.yaml to match event string
        '''
        # TODO: obj_type ('ems' or 'vm') is the same for all tests in class
        #       there must be a better way than to pass this around
        ems_map = {"rhevm": "EmsRedhat",
                        "virtualcenter": "EmsVmware"}
        vm_map = {"rhevm": "VmRedhat",
                        "virtualcenter": "VmVmware"}
        if obj_type in "ems":
            return ems_map.get(sys_type)
        elif obj_type in "vm":
            return vm_map.get(sys_type)


@pytest.fixture(scope="module")
def api_methods(request, cfme_data):
    return APIMethods(cfme_data.data)


@pytest.mark.destructive  # IGNORE:E1101
class TestCustomizeAutomate():
    '''Setup tests to prepare appliance for events testing
    '''
    @pytest.mark.skip_selenium
    def test_import_namespace(self, mozwebqa, cfme_data, ssh_client):
        '''Update custom automate namespace xml file with listener URL,
           copy to appliance, import using rake method
        '''
        qe_automate_namespace_xml = "qe_event_handler.xml"
        local_automate_file = "%s/tests/ui/integration/data/%s" % \
            (mozwebqa.request.session.fspath, qe_automate_namespace_xml)
        tmp_automate_file = "/tmp/%s" % qe_automate_namespace_xml

        # create temp xml file to work with
        shutil.copyfile(local_automate_file, tmp_automate_file)

        # update temp xml file with listener IP address from cfme_data
        listener_url = cfme_data.data['listener']['url'].strip('http://')
        with open(tmp_automate_file, "r") as sources:
            lines = sources.readlines()
        with open(tmp_automate_file, "w") as sources:
            for line in lines:
                sources.write(re.sub(r'localhost', listener_url, line))

        # copy xml file to appliance
        ssh_client.put_file(tmp_automate_file, '/root/')

        # run rake cmd on appliance to import automate namespace
        rake_cmd = "evm:automate:import FILE=/root/%s" % \
            qe_automate_namespace_xml
        ssh_client.run_rake_command(rake_cmd)

    @pytest.mark.usefixtures("maximized")  # IGNORE:E1101
    def test_create_automate_instance_hook(self, automate_explorer_pg):
        '''Add automate instance that follows relationship to custom namespace
        '''
        parent_class = "Automation Requests (Request)"
        instance_details = [
            "RelayEvents", 
            "RelayEvents", 
            "relationship hook to link to custom QE events relay namespace"
            ]
        instance_row = 2
        instance_value = "/QE/Automation/APIMethods/relay_events?event=$evm.object['event']"

        class_pg = automate_explorer_pg.click_on_class_access_node(parent_class)
        instance_pg = class_pg.click_on_add_new_instance()
        instance_pg.fill_instance_info(*instance_details)
        instance_pg.fill_instance_field_row_info(instance_row, instance_value)
        class_pg = instance_pg.click_on_add_system_button()
        Assert.equal(class_pg.flash_message_class, 
            'Automate Instance "%s" was added' % instance_details[0])

    @pytest.mark.usefixtures("maximized")
    def test_import_policies(self, request, home_page_logged_in):
        '''Import policy profile that raises automate model based on events
        '''
        policy_yaml = "profile_relay_events.yaml"
        policy_path = "%s/tests/ui/integration/data/%s" % \
            (request.session.fspath, policy_yaml)

        home_pg = home_page_logged_in
        import_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Import / Export").click()
        import_pg = import_pg.import_policies(policy_path)
        Assert.equal(import_pg.flash.message, "Press commit to Import")
        import_pg = import_pg.click_on_commit()
        Assert.equal(import_pg.flash.message, 
            "Import file was uploaded successfully")

    @pytest.mark.usefixtures("maximized")  # IGNORE:E1101
    def test_assign_policy_profile(self, setup_infrastructure_providers, infra_providers_pg, mgmt_sys):
        '''Assign policy profile to management system
        '''
        policy_profile = "Automate event policies"
        infra_providers_pg.select_provider(mgmt_sys['name'])
        policy_pg = infra_providers_pg.click_on_manage_policies()
        policy_pg.select_profile_item(policy_profile)
        policy_pg.save()
        Assert.equal(policy_pg.flash.message,
            'Policy assignments successfully changed',
            'Save policy assignment flash message did not match')


@pytest.mark.usefixtures("maximized")  # IGNORE:E1101
class TestVmPowerEvents():
    '''Toggle power state of VM(s) listed in cfme_data.yaml under 
       'test_vm_power_control' and verify event(s) passed through automate
       and into running event listener

       Listener is managed by fixture setup_api_listener
       Listener code is tests/common/listener.py
    '''

    def test_vm_power_on_ui(self, setup_api_listener, infra_vms_pg, mgmt_sys, api_methods):
        '''Power on guest via UI
        '''
        for vm in mgmt_sys['test_vm_power_control']:
            infra_vms_pg.wait_for_vm_state_change(vm, 'off', 3)
            vm_pg = infra_vms_pg.find_vm_page(vm, 'off', True, True)
            vm_pg.power_button.power_on()
            events = ["vm_power_on_req", "vm_power_on"]
            for event in events:
                Assert.true(api_methods.check_db(
                    mgmt_sys['type'], "vm", vm, event))

    def test_vm_power_off_ui(self, infra_vms_pg, mgmt_sys, api_methods):
        '''Power off guest via UI
        '''
        for vm in mgmt_sys['test_vm_power_control']:
            infra_vms_pg.wait_for_vm_state_change(vm, 'on', 3)
            vm_pg = infra_vms_pg.find_vm_page(vm, 'on', True, True)
            vm_pg.power_button.power_off()
            Assert.true(api_methods.check_db(
                mgmt_sys['type'], "vm", vm, "vm_power_off"))
