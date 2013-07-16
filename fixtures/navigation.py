'''
Created on Jul 9, 2013

@author: bcrochet
'''
# -*- coding: utf8 -*-
# pylint: disable=E1101
import pytest
from unittestzero import Assert

@pytest.fixture
def home_page_logged_in(mozwebqa):
    '''Logs in to the application with default credentials and returns the 
    home page'''
    from pages.login import LoginPage
    login_pg = LoginPage(mozwebqa)
    login_pg.go_to_login_page()
    home_pg = login_pg.login()
    Assert.true(home_pg.is_logged_in, 'Could not determine if logged in')
    return home_pg

@pytest.fixture
def configuration_pg(home_page_logged_in):
    '''Navigate to the Configuration -> Configuration page and return it'''
    return home_page_logged_in.header.site_navigation_menu(
            'Configuration').sub_navigation_menu('Configuration').click()

def _services_submenu(home_pg, submenu):
    return home_pg.header.site_navigation_menu(
            'Services').sub_navigation_menu(submenu).click()

@pytest.fixture
def svc_myservices_pg(home_page_logged_in):
    '''Navigate to Services -> My Services page and return it'''
    return _services_submenu(home_page_logged_in, 'My Services')

@pytest.fixture
def svc_vms_pg(home_page_logged_in):
    '''Navigate to Services -> Virtual Machines page and return it'''
    return _services_submenu(home_page_logged_in, 'Virtual Machines')

def _infrastructure_submenu(home_pg, submenu):
    return home_pg.header.site_navigation_menu(
            'Infrastructure').sub_navigation_menu(submenu).click()

@pytest.fixture
def infra_providers_pg(home_page_logged_in):
    '''Navigate to Infrastructure -> Providers page and return it'''
    return _infrastructure_submenu(home_page_logged_in, 'Providers')

@pytest.fixture
def infra_clusters_pg(home_page_logged_in):
    '''Navigate to Infrastructure -> Clusters page and return it'''
    return _infrastructure_submenu(home_page_logged_in, 'Clusters')

@pytest.fixture
def infra_hosts_pg(home_page_logged_in):
    '''Navigate to Infrastructure -> Hosts page and return it'''
    return _infrastructure_submenu(home_page_logged_in, 'Hosts')

@pytest.fixture
def infra_datastores_pg(home_page_logged_in):
    '''Navigate to Infrastructure -> Datastores page and return it'''
    return _infrastructure_submenu(home_page_logged_in, 'Datastores')

@pytest.fixture # IGNORE:E1101
def infra_pxe_pg(home_page_logged_in):
    '''Navigate to Infrastructure -> PXE page and return it'''
    return _infrastructure_submenu(home_page_logged_in, 'PXE')

@pytest.fixture
def automate_explorer_pg(home_page_logged_in):
    '''Navigate to Automate -> Explorer'''
    return home_page_logged_in.header.site_navigation_menu(
            "Automate").sub_navigation_menu("Explorer").click()
