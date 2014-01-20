"""Navigation fixtures for use in tests."""
# -*- coding: utf8 -*-
from functools import partial

import pytest
from selenium.common.exceptions import NoAlertPresentException

from pages.login import LoginPage
from utils.browser import browser, ensure_browser_open, testsetup

_width_errmsg = '''The minimum supported width of CFME is 1280 pixels

Some navigation fixtures will fail if the browser window is too small
due to submenu elements being rendered off the screen.
'''


@pytest.fixture
def home_page_logged_in(testsetup=testsetup):
    return intel_dashboard_pg()


def _squash_alert():
    try:
        alert = browser().switch_to_alert()
        alert.accept()
    except NoAlertPresentException:
        pass


def navigate(first_level, second_level):
    # Make sure a browser is running
    ensure_browser_open()
    # Clear any potential permaspinnies before moving on
    browser().execute_script('miqSparkleOff();')

    # Ensure browser is logged in as admin, reinitialize page to pick up any browser changes
    page = LoginPage(testsetup)
    if not page.is_logged_in or page.header.username != 'Administrator':
        page.go_to_login_page()
        # Close any alerts that happen when switching to the login page
        _squash_alert()
        page = page.login()
        assert page.is_logged_in

    # Do the navigation
    first = page.header.site_navigation_menu(first_level)
    second = first.sub_navigation_menu(second_level)
    destination = second.click()
    # Close any alerts that happen on the navigation click
    _squash_alert()

    return destination


def navigator(first_level, second_level):
    # Adds a _navigate method to a Page, as well as makes fixtures
    # themselves callable using the same method.
    # This is evil, but transitional.
    navigator = partial(navigate, first_level, second_level)
    page = navigator()
    type(page).__call__ = navigator
    return page


@pytest.fixture
def cnf_configuration_pg():
    return navigator('Configure', 'Configuration')


@pytest.fixture
def cnf_about_pg():
    return navigator('Configure', 'About')


@pytest.fixture
def cnf_mysettings_pg():
    return navigator('Configure', 'My Settings')


@pytest.fixture
def cnf_tasks_pg():
    return navigator('Configure', 'Tasks')


@pytest.fixture
def cnf_smartproxies_pg():
    return navigator('Configure', 'SmartProxies')


@pytest.fixture
def svc_myservices_pg():
    return navigator('Services', 'My Services')


@pytest.fixture
def svc_catalogs_pg():
    return navigator('Services', 'Catalogs')


@pytest.fixture
def cloud_providers_pg():
    return navigator('Clouds', 'Providers')


@pytest.fixture
def cloud_availabilityzones_pg():
    return navigator('Clouds', 'Availability Zones')


@pytest.fixture
def cloud_flavors_pg():
    return navigator('Clouds', 'Flavors')


@pytest.fixture
def cloud_securitygroups_pg():
    return navigator('Clouds', 'Security Groups')


@pytest.fixture
def cloud_instances_pg():
    return navigator('Clouds', 'Instances')


@pytest.fixture
def infra_providers_pg():
    return navigator('Infrastructure', 'Providers')


@pytest.fixture
def infra_clusters_pg():
    return navigator('Infrastructure', 'Clusters')


@pytest.fixture
def infra_hosts_pg():
    return navigator('Infrastructure', 'Hosts')


@pytest.fixture
def infra_datastores_pg():
    return navigator('Infrastructure', 'Datastores')


@pytest.fixture
def infra_pxe_pg():
    return navigator('Infrastructure', 'PXE')


@pytest.fixture
def infra_vms_pg():
    return navigator('Infrastructure', 'Virtual Machines')


@pytest.fixture
def automate_explorer_pg():
    return navigator('Automate', 'Explorer')


@pytest.fixture
def automate_importexport_pg():
    return navigator('Automate', 'Import / Export')


@pytest.fixture
def automate_customization_pg():
    return navigator('Automate', 'Customization')


@pytest.fixture
def control_explorer_pg():
    return navigator('Control', 'Explorer')


@pytest.fixture
def control_importexport_pg():
    return navigator('Control', 'Import / Export')


@pytest.fixture
def control_simulation_pg():
    return navigator('Control', 'Simulation')


@pytest.fixture
def control_log_pg():
    return navigator('Control', 'Log')


@pytest.fixture
def optimize_utilization_pg():
    return navigator('Optimize', 'Utilization')


@pytest.fixture
def intel_dashboard_pg():
    return navigator('Cloud Intelligence', 'Dashboard')


@pytest.fixture
def intel_chargeback_pg():
    return navigator('Cloud Intelligence', 'Chargeback')


@pytest.fixture
def intel_reports_pg():
    return navigator('Cloud Intelligence', 'Reports')
