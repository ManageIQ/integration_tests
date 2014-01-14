"""Navigation fixtures for use in tests."""
# -*- coding: utf8 -*-
from functools import partial

import pytest
from unittestzero import Assert

from utils.browser import start, testsetup

_width_errmsg = '''The minimum supported width of CFME is 1280 pixels

Some navigation fixtures will fail if the browser window is too small
due to submenu elements being rendered off the screen.
'''


@pytest.fixture
def home_page_logged_in(testsetup=testsetup):
    """Log in to the appliance and return the home page."""
    start()

    from pages.login import LoginPage
    login_pg = LoginPage(testsetup)
    login_pg.go_to_login_page()
    home_pg = login_pg.login()
    Assert.true(login_pg.is_logged_in, 'Could not determine if logged in')
    return home_pg


def navigate(page, first_level, second_level):
    first_level = page.header.site_navigation_menu(first_level)
    second_level = first_level.sub_navigation_menu(second_level)
    return second_level.click()


class NavigationFixture(object):
    def __new__(cls, page_obj, first_level, second_level):
        # Adds a _navigate method to a Page, as well as makes fixtures
        # themselves callable using the same method.
        # This is evil, but transitional.
        navigator = partial(navigate, page_obj, first_level, second_level)
        page = navigator()
        type(page)._navigate = navigator

        def __call__(self):
            self._navigate()
        type(page).__call__ = __call__
        return page


# In all following fixtures, the "page" argument is not required
# It is included for backward-compatibility only
@pytest.fixture
def cnf_configuration_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Configure', 'Configuration')


@pytest.fixture
def cnf_about_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Configure', 'About')


@pytest.fixture
def cnf_mysettings_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Configure', 'My Settings')


@pytest.fixture
def cnf_tasks_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Configure', 'Tasks')


@pytest.fixture
def cnf_smartproxies_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Configure', 'SmartProxies')


@pytest.fixture
def svc_myservices_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Services', 'My Services')


@pytest.fixture
def svc_catalogs_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Services', 'Catalogs')


@pytest.fixture
def cloud_providers_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Clouds', 'Providers')


@pytest.fixture
def cloud_availabilityzones_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Clouds', 'Availability Zones')


@pytest.fixture
def cloud_flavors_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Clouds', 'Flavors')


@pytest.fixture
def cloud_securitygroups_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Clouds', 'Security Groups')


@pytest.fixture
def cloud_instances_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Clouds', 'Instances')


@pytest.fixture
def infra_providers_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Infrastructure', 'Providers')


@pytest.fixture
def infra_clusters_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Infrastructure', 'Clusters')


@pytest.fixture
def infra_hosts_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Infrastructure', 'Hosts')


@pytest.fixture
def infra_datastores_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Infrastructure', 'Datastores')


@pytest.fixture
def infra_pxe_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Infrastructure', 'PXE')


@pytest.fixture
def infra_vms_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Infrastructure', 'Virtual Machines')


@pytest.fixture
def automate_explorer_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Automate', 'Explorer')


@pytest.fixture
def automate_importexport_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Automate', 'Import / Export')


@pytest.fixture
def automate_customization_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Automate', 'Customization')


@pytest.fixture
def control_explorer_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Control', 'Explorer')


@pytest.fixture
def control_importexport_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Control', 'Import / Export')


@pytest.fixture
def control_simulation_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Control', 'Simulation')


@pytest.fixture
def control_log_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Control', 'Log')


@pytest.fixture
def optimize_utilization_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Optimize', 'Utilization')


@pytest.fixture
def intel_dashboard_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Cloud Intelligence', 'Dashboard')


@pytest.fixture
def intel_chargeback_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Cloud Intelligence', 'Chargeback')


@pytest.fixture
def intel_reports_pg(page=None):
    return NavigationFixture(home_page_logged_in(), 'Cloud Intelligence', 'Reports')
