# -*- coding: utf8 -*-
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


def _submenu(home_pg, main_menu, submenu):
    return home_pg.header.site_navigation_menu(main_menu)\
        .sub_navigation_menu(submenu).click()


@pytest.fixture
def cnf_configuration_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Configure', 'Configuration')


@pytest.fixture
def cnf_about_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Configure', 'About')


@pytest.fixture
def cnf_mysettings_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Configure', 'My Settings')


@pytest.fixture
def cnf_tasks_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Configure', 'Tasks')


@pytest.fixture
def cnf_smartproxies_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Configure', 'SmartProxies')


@pytest.fixture
def svc_myservices_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Services', 'My Services')


@pytest.fixture
def svc_catalogs_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Services', 'Catalogs')


@pytest.fixture
def cloud_providers_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Clouds', 'Providers')


@pytest.fixture
def cloud_availabilityzones_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Clouds', 'Availability Zones')


@pytest.fixture
def cloud_flavors_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Clouds', 'Flavors')


@pytest.fixture
def cloud_securitygroups_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Clouds', 'Security Groups')


@pytest.fixture
def cloud_instances_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Clouds', 'Instances')


@pytest.fixture
def infra_providers_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Infrastructure', 'Providers')


@pytest.fixture
def infra_clusters_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Infrastructure', 'Clusters')


@pytest.fixture
def infra_hosts_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Infrastructure', 'Hosts')


@pytest.fixture
def infra_datastores_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Infrastructure', 'Datastores')


@pytest.fixture
def infra_pxe_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Infrastructure', 'PXE')


@pytest.fixture
def infra_vms_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Infrastructure', 'Virtual Machines')


@pytest.fixture
def automate_explorer_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Automate', 'Explorer')


@pytest.fixture
def automate_importexport_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Automate', 'Import / Export')


@pytest.fixture
def automate_customization_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Automate', 'Customization')


@pytest.fixture
def control_explorer_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Control', 'Explorer')


@pytest.fixture
def control_importexport_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Control', 'Import / Export')


@pytest.fixture
def optimize_utilization_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Optimize', 'Utilization')


@pytest.fixture
def intel_chargeback_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Cloud Intelligence', 'Chargeback')


@pytest.fixture
def intel_reports_pg(home_page_logged_in):
    return _submenu(home_page_logged_in, 'Cloud Intelligence', 'Reports')
