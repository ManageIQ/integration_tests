'''
Created on Mar 4, 2013

@author: bcrochet
'''
import pytest
from unittestzero import Assert
import time
from common.MgmtSystem import VMWareSystem, RHEVMSystem

@pytest.fixture # IGNORE:E1101
def home_page_logged_in(mozwebqa):
    from pages.login import LoginPage
    login_pg = LoginPage(mozwebqa)
    login_pg.go_to_login_page()
    home_pg = login_pg.login()
    Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
    return home_pg

@pytest.fixture  # IGNORE:E1101
def setup_mgmt_systems(home_page_logged_in, cfme_data):    
    # Does mgmt system exist
    for provider in cfme_data.data["management_systems"]:
        ms_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        mgmt_data = cfme_data.data["management_systems"][provider]
        mgmt_cred = ms_pg.testsetup.credentials[mgmt_data["credentials"]]
        mgmt_added = False
        if (len(ms_pg.quadicon_region.quadicons) == 0) or not ms_pg.quadicon_region.does_quadicon_exist(mgmt_data["name"]):
            # add it
            add_pg = ms_pg.click_on_add_new_management_system()
            add_pg.new_management_system_fill_data(mgmt_data["name"],mgmt_data["hostname"],mgmt_data["ipaddress"], mgmt_cred["username"], mgmt_cred["password"])
            if mgmt_data["type"] == "virtualcenter":
                add_pg.select_management_system_type("VMware vCenter")
            elif mgmt_data["type"] == "rhevm":
                add_pg.select_management_system_type("Red Hat Enterprise Virtualization Manager")
            else:
                add_pg.select_management_system_type(mgmt_data["type"])
            ms_pg = add_pg.click_on_add()
            Assert.true(ms_pg.flash.message == "Management System \""+ mgmt_data["name"] +"\" was saved")
            mgmt_added = True

            # wait for the quadicon to show up
            sleep_time = 1
            while not ms_pg.quadicon_region.does_quadicon_exist(mgmt_data["name"]):
                ms_pg.selenium.refresh()
                time.sleep(sleep_time)
                sleep_time *= 2
                if sleep_time > 90:
                    raise Exception("timeout reached for mgmt_system icon to show up")

        # Are the credentials valid?
        mgmt_quadicon = ms_pg.quadicon_region.get_quadicon_by_title(mgmt_data["name"])
        valid_creds = mgmt_quadicon.valid_credentials
        if mgmt_added and not valid_creds:
            sleep_time = 1
            while not valid_creds:
                ms_pg.selenium.refresh()
                time.sleep(sleep_time)
                mgmt_quadicon = ms_pg.quadicon_region.get_quadicon_by_title(mgmt_data["name"])
                valid_creds = mgmt_quadicon.valid_credentials
                sleep_time *= 2
                if sleep_time > 90:
                    raise Exception("timeout reached for valid mgmt_system credentials")
        elif not mgmt_quadicon.valid_credentials:
            # update them
            ms_pg.select_management_system(mgmt_data["name"])
            Assert.true(len(ms_pg.quadicon_region.selected) == 1, "More than one quadicon was selected")
            mse_pg = ms_pg.click_on_edit_management_systems()
            mse_pg.edit_management_system(mgmt_data)    

@pytest.fixture
def maximized(mozwebqa):
    mozwebqa.selenium.maximize_window()
    return True

@pytest.fixture(scope='module') # IGNORE:E1101
def mgmt_sys_api_clients(mozwebqa, cfme_data):
    clients = {}
    for sys_name, mgmt_sys in cfme_data.data['management_systems'].items():
        cred = mgmt_sys['credentials'].strip()
        host = mgmt_sys['ipaddress']
        user = mozwebqa.credentials[cred]['username']
        pwd = mozwebqa.credentials[cred]['password']
        sys_type = mgmt_sys['type']

        if 'virtual' in sys_type.lower():
            # create pysphere client
            client = VMWareSystem(hostname=host, 
                    username=user, 
                    password=pwd)
            if sys_name in clients:
                # Overlapping sys_name entry in cfme_data.yaml
                logging.warning('Overriding existing entry for %s.' % sys_name)
            clients[sys_name] = client
        elif 'rhevm' in sys_type.lower():
        # create rhevm client
            client = RHEVMSystem(hostname=host, 
                    username=user, 
                    password=pwd)
            if sys_name in clients:
                # Overlapping sys_name entry in cfme_data.yaml
                logging.warning('Overriding existing entry for %s.' % sys_name)
            clients[sys_name] = client
        else:
            logging.info('Can\'t create client for %s, ignoring...' % sys_name)
    return clients
