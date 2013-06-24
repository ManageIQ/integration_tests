#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
import os
import re
import subprocess
import requests
import logging
from urlparse import urlparse

#
# This test requires complex setup so events can be validated through automate.
# The API listener (bottle) runs alongside this test as a bridge between
# automate and py.test. See tests/common/listener.py
#

# Global var used to record listener process info
listener = None

logging.basicConfig(filename='test_events.log', level=logging.INFO)


def setup_module(module):
    global listener
    listener_script = "/usr/bin/env python tests/common/listener.py"
    logging.info("Starting listener ... ")
    listener = subprocess.Popen(listener_script,
            stderr=subprocess.PIPE,
            shell=True)
    logging.info("(%s)\n" % listener.pid)
    # Wait for listener to start ...
    time.sleep(1)


def teardown_module(module):
    global listener
    logging.info("\nKilling listener (%s)..." % (listener.pid))
    listener.kill()
    (stdout, stderr) = listener.communicate()
    logging.info("%s\n%s" % (stdout, stderr))


@pytest.fixture(scope="module",  # IGNORE:E1101
                params=["rhevm31"])
def mgmt_sys(request, cfme_data):
    param = request.param
    return cfme_data.data['management_systems'][param]


class APIMethods():
    def __init__(self, cfme_data):
        self.listener_host = cfme_data['listener']

    def get(self, route):
        listener_url = "%s:%s" % (self.listener_host['url'], self.listener_host['port'])
        logging.debug("api request to %s%s" % (listener_url, route))
        r = requests.get(listener_url + route)
        r.raise_for_status()
        return r.json

    def check_db(self, sys_type, obj_type, obj, event):
        '''Utility to check listener database for event
        '''
        max_attempts = 24
        sleep_interval = 10 
        req = "/events/%s/%s?event=%s" % (self.mgmt_sys_type(sys_type, obj_type), obj, event)
        for attempt in range(1, max_attempts+1):
            try:
                assert len(self.get(req)) == 1
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
        # FIXME: obj_type ('ems' or 'vm') is the same for all tests in class
        #        there must be a better way than to pass this around
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
    @pytest.mark.skip_selenium
    def test_import_namespace(self, mozwebqa, cfme_data, ssh_client):
        '''Update custom automate namespace xml file with listener URL,
           copy to appliance, import using rake method
        '''
        # FIXME: custom automate ruby script doesn't support spaces in 
        #        mgmt_system name. Need to url-encode url string in ruby method
        qe_automate_namespace_xml = "qe_event_handler.xml"
        qe_automate_path = os.getcwd() + "/tests/ui/integration/data/" + qe_automate_namespace_xml
        rake_cmd = "evm:automate:import FILE=/root/%s" % qe_automate_namespace_xml
        listener_url = cfme_data.data['listener']['url'].strip('http://')

        # update xml file
        with open(qe_automate_path, "r") as sources:
            lines = sources.readlines()
        with open(qe_automate_path, "w") as sources:
            for line in lines:
                sources.write(re.sub(r'localhost', listener_url, line))

        # copy xml file to appliance
        parsed_url = urlparse(mozwebqa.base_url)
        os.system("sshpass -p '%s' scp %s %s@%s:/root/" % 
            (mozwebqa.credentials['ssh']['password'], 
             qe_automate_path, 
             mozwebqa.credentials['ssh']['username'], 
             parsed_url.hostname))

        # run rake cmd on appliance to import xml
        ssh_client.run_rake_command(rake_cmd)

    @pytest.mark.usefixtures("maximized") # IGNORE:E1101
    def test_create_automate_instance_hook(self, automate_explorer_pg):
        '''Add automate instance that follows relationship to custom namespace
        '''
        parent_class = "Automation Requests (Request)"
        instance_details = ["RelayEvents", "RelayEvents", "relationship hook to link to custom QE events relay namespace"]
        instance_row = 2
        instance_value = "/QE/Automation/APIMethods/relay_events?event=$evm.object['event']"

        class_pg = automate_explorer_pg.click_on_class_access_node(parent_class)
        instance_pg = class_pg.click_on_add_new_instance()
        instance_pg.fill_instance_info(*instance_details)
        instance_pg.fill_instance_field_row_info(instance_row, instance_value)
        class_pg = instance_pg.click_on_add_system_button()
        Assert.true(class_pg.flash_message_class == 'Automate Instance "%s" was added' % instance_details[0])

    @pytest.mark.usefixtures("maximized")
    def test_import_policies(self, home_page_logged_in):
        '''Import policy profile that raises automate model based on events
        '''
        policy_yaml = "profile_relay_events.yaml"
        policy_path = os.getcwd() + "/tests/ui/integration/data/" + policy_yaml

        home_pg = home_page_logged_in
        import_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Import / Export").click()
        import_pg = import_pg.import_policies(policy_path)
        Assert.true(import_pg.flash.message == "Press commit to Import")
        import_pg = import_pg.click_on_commit()
        Assert.true(import_pg.flash.message == "Import file was uploaded successfully")

    @pytest.mark.usefixtures("maximized")  # IGNORE:E1101
    def test_assign_policy_profile(self, setup_infrastructure_providers, infra_providers_pg, mgmt_sys):
        '''Assign policy profile to management system
        '''
        profile = "Automate event policies"
        infra_providers_pg.select_provider(mgmt_sys['name'])
        policy_pg = infra_providers_pg.click_on_manage_policies()
        policy_pg.select_profile_item(profile)
        policy_pg.save()
        Assert.true(policy_pg.flash.message.startswith(
                'Policy assignments successfully changed'))


@pytest.mark.usefixtures("maximized")  # IGNORE:E1101
class TestVmPowerEvents():
    '''Toggle power state of VM(s) listed in cfme_data.yaml under 
       'test_vm_power_control' and verify event(s) passed through automate
       and into running event listener
    '''

    def test_vm_power_on_ui(self, infra_vms_pg, mgmt_sys, api_methods):
        '''Power on guest via UI
        '''
        for vm in mgmt_sys['test_vm_power_control']:
            infra_vms_pg.wait_for_vm_state_change(vm, 'off', 3)
            vm_pg = infra_vms_pg.find_vm_page(vm, 'off', True, True)
            vm_pg.power_button.power_on()
            events = ["vm_power_on_req", "vm_power_on"]
            for event in events:
                assert api_methods.check_db(mgmt_sys['type'], "vm", vm, event)

    def test_vm_power_off_ui(self, infra_vms_pg, mgmt_sys, api_methods):
        '''Power off guest via UI
        '''
        for vm in mgmt_sys['test_vm_power_control']:
            infra_vms_pg.wait_for_vm_state_change(vm, 'on', 3)
            vm_pg = infra_vms_pg.find_vm_page(vm, 'on', True, True)
            vm_pg.power_button.power_off()
            assert api_methods.check_db(mgmt_sys['type'], "vm", vm, "vm_power_off")
