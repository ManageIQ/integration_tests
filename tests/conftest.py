"""
Created on Mar 4, 2013

@author: bcrochet
"""
# pylint: disable=E1101
import logging
import time
import random
import pytest
from unittestzero import Assert

from common.mgmt_system import VMWareSystem, RHEVMSystem, EC2System

logger = logging.getLogger(__name__)

@pytest.fixture
def maximized(mozwebqa):
    '''Maximizes the browser window'''
    mozwebqa.selenium.maximize_window()
    return True

@pytest.fixture  # IGNORE:E1101
def setup_infrastructure_providers(home_page_logged_in, cfme_data):
    '''Adds all providers listed in cfme_data.yaml'''
    # Does provider exist
    for provider in cfme_data.data['management_systems']:
        prov_pg = home_page_logged_in.header.site_navigation_menu(
                'Infrastructure').sub_navigation_menu('Providers').click()
        prov_data = cfme_data.data['management_systems'][provider]
        prov_cred = prov_pg.testsetup.credentials[prov_data['credentials']]
        prov_added = False
        prov_pg.taskbar_region.view_buttons.change_to_grid_view()
        Assert.true(prov_pg.taskbar_region.view_buttons.is_grid_view)
        if (len(prov_pg.quadicon_region.quadicons) == 0) \
                or not prov_pg.quadicon_region.does_quadicon_exist(
                        prov_data['name']):
            # add it
            add_pg = prov_pg.click_on_add_new_provider()
            add_pg.new_provider_fill_data(
                    prov_data['name'],
                    prov_data['hostname'],
                    prov_data['ipaddress'],
                    prov_cred['username'],
                    prov_cred['password'])
            if prov_data['type'] == 'virtualcenter':
                add_pg.select_provider_type('VMware vCenter')
            elif prov_data['type'] == 'rhevm':
                add_pg.select_provider_type(
                        'Red Hat Enterprise Virtualization Manager')
            elif prov_data['type'] == 'ec2':
                add_pg.select_provider_type('Amazon EC2')
            else:
                add_pg.select_provider_type(prov_data['type'])
            prov_pg = add_pg.click_on_add()
            Assert.equal(prov_pg.flash.message,
                    'Infrastructure Providers "%s" was saved'
                            % prov_data['name'],
                    'Flash message did not match')
            prov_added = True

            # wait for the quadicon to show up
            sleep_time = 1
            prov_pg.taskbar_region.view_buttons.change_to_grid_view()
            Assert.true(prov_pg.taskbar_region.view_buttons.is_grid_view)
            while not prov_pg.quadicon_region.does_quadicon_exist(
                    prov_data['name']):
                prov_pg.selenium.refresh()
                time.sleep(sleep_time)
                sleep_time *= 2
                if sleep_time > 90:
                    raise Exception(
                            'timeout reached for provider icon to show up')

        # Are the credentials valid?
        prov_pg.taskbar_region.view_buttons.change_to_grid_view()
        Assert.true(prov_pg.taskbar_region.view_buttons.is_grid_view)
        prov_quadicon = prov_pg.quadicon_region.get_quadicon_by_title(
                prov_data['name'])
        valid_creds = prov_quadicon.valid_credentials
        if prov_added and not valid_creds:
            sleep_time = 1
            while not valid_creds:
                prov_pg.selenium.refresh()
                time.sleep(sleep_time)
                prov_quadicon = prov_pg.quadicon_region.get_quadicon_by_title(
                        prov_data['name'])
                valid_creds = prov_quadicon.valid_credentials
                sleep_time *= 2
                if sleep_time > 90:
                    raise Exception(
                            'timeout reached for valid provider credentials')
        elif not prov_quadicon.valid_credentials:
            # update them
            prov_pg.select_provider(prov_data['name'])
            Assert.equal(len(prov_pg.quadicon_region.selected), 1,
                    'More than one quadicon was selected')
            prov_edit_pg = prov_pg.click_on_edit_providers()
            prov_edit_pg.edit_provider(prov_data)

@pytest.fixture(scope='module')  # IGNORE:E1101
def mgmt_sys_api_clients(mozwebqa, cfme_data):
    '''Returns a list of management system api clients'''
    clients = {}
    for sys_name, mgmt_sys in cfme_data.data['management_systems'].items():
        cred = mgmt_sys['credentials'].strip()
        host = mgmt_sys['ipaddress']
        user = mozwebqa.credentials[cred]['username']
        pwd = mozwebqa.credentials[cred]['password']
        sys_type = mgmt_sys['type']

        if 'virtual' in sys_type.lower():
            client = VMWareSystem(
                hostname=host,
                username=user,
                password=pwd
            )
        elif 'rhevm' in sys_type.lower():
            client = RHEVMSystem(
                hostname=host,
                username=user,
                password=pwd
            )
        elif 'ec2' in sys_type.lower():
            client = EC2System(
                access_key_id=user,
                secret_access_key=pwd
            )
        else:
            logger.info("Can't create client for %s, ignoring..." % sys_name)
            continue

        if sys_name in clients:
            # Overlapping sys_name entry in cfme_data.yaml
            logger.warning('Overriding existing entry for %s.' % sys_name)
        clients[sys_name] = client
        # unbind the 'client' identifier for the next iteration
        del client

    return clients


