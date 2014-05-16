"""Navigation fixtures for use in tests."""
# -*- coding: utf8 -*-
from functools import partial
import warnings

import pytest

from cfme.fixtures.pytest_selenium import force_navigate
from pages.base import Base
from utils.browser import testsetup
from utils.log import logger


_width_errmsg = '''The minimum supported width of CFME is 1280 pixels

Some navigation fixtures will fail if the browser window is too small
due to submenu elements being rendered off the screen.
'''

_warn_msg = '''fixtures.navigation will be deprecated in the future. \
Please use the pytest.sel.go_to test decorator.'''


@pytest.fixture
def home_page_logged_in(testsetup=testsetup):
    return intel_dashboard_pg()


def navigate(page_name, first_level, second_level):
    """Navigate function that represents the old navigation fixtures.

    Args:
        page_name: The page name.
        first_level: The first level of nav.
        second_level: The second level of nav.

    """
    warnings.warn(_warn_msg, FutureWarning)
    from pages.regions.header_menu import HeaderMenu
    try:
        page_class = HeaderMenu.HeaderMenuItem._item_page[first_level][second_level]
    except KeyError:
        logger.info("Couldn't find page class when navigating to '%s', using Base" % page_name)
        page_class = Base

    # Make the return of navigate be a callable that does the same work
    # so that fixtures can be called again to navigate.
    page_class.__call__ = partial(navigate, page_name, first_level, second_level)

    force_navigate(page_name)
    return page_class(testsetup)


@pytest.fixture
def cnf_configuration_pg():
    return navigate('configuration', 'Configure', 'Configuration')


@pytest.fixture
def cnf_about_pg():
    return navigate('about', 'Configure', 'About')


@pytest.fixture
def cnf_mysettings_pg():
    return navigate('my_settings', 'Configure', 'My Settings')


@pytest.fixture
def cnf_tasks_pg():
    return navigate('tasks', 'Configure', 'Tasks')


@pytest.fixture
def cnf_smartproxies_pg():
    return navigate('smartproxies', 'Configure', 'SmartProxies')


@pytest.fixture
def svc_myservices_pg():
    return navigate('my_services', 'Services', 'My Services')


@pytest.fixture
def svc_catalogs_pg():
    return navigate('services_catalogs', 'Services', 'Catalogs')


@pytest.fixture
def cloud_providers_pg():
    return navigate('clouds_providers', 'Clouds', 'Providers')


@pytest.fixture
def cloud_availabilityzones_pg():
    return navigate('clouds_availability_zones', 'Clouds', 'Availability Zones')


@pytest.fixture
def cloud_flavors_pg():
    return navigate('clouds_flavors', 'Clouds', 'Flavors')


@pytest.fixture
def cloud_securitygroups_pg():
    return navigate('clouds_security_groups', 'Clouds', 'Security Groups')


@pytest.fixture
def cloud_instances_pg():
    return navigate('clouds_instances', 'Clouds', 'Instances')


@pytest.fixture
def infra_providers_pg():
    return navigate('infrastructure_providers', 'Infrastructure', 'Providers')


@pytest.fixture
def infra_clusters_pg():
    return navigate('infrastructure_clusters', 'Infrastructure', 'Clusters')


@pytest.fixture
def infra_hosts_pg():
    return navigate('infrastructure_hosts', 'Infrastructure', 'Hosts')


@pytest.fixture
def infra_datastores_pg():
    return navigate('infrastructure_datastores', 'Infrastructure', 'Datastores')


@pytest.fixture
def infra_pxe_pg():
    return navigate('infrastructure_pxe', 'Infrastructure', 'PXE')


@pytest.fixture
def infra_vms_pg():
    return navigate('infrastructure_virtual_machines', 'Infrastructure', 'Virtual Machines')


@pytest.fixture
def automate_explorer_pg():
    return navigate('automate_explorer', 'Automate', 'Explorer')


@pytest.fixture
def automate_importexport_pg():
    return navigate('automate_import_export', 'Automate', 'Import / Export')


@pytest.fixture
def automate_customization_pg():
    return navigate('automate_customization', 'Automate', 'Customization')


@pytest.fixture
def control_explorer_pg():
    return navigate('control_explorer', 'Control', 'Explorer')


@pytest.fixture
def control_importexport_pg():
    return navigate('control_import_export', 'Control', 'Import / Export')


@pytest.fixture
def control_simulation_pg():
    return navigate('control_simulation', 'Control', 'Simulation')


@pytest.fixture
def control_log_pg():
    return navigate('control_log', 'Control', 'Log')


@pytest.fixture
def optimize_utilization_pg():
    return navigate('utilization', 'Optimize', 'Utilization')


@pytest.fixture
def intel_dashboard_pg():
    return navigate('dashboard', 'Cloud Intelligence', 'Dashboard')


@pytest.fixture
def intel_chargeback_pg():
    return navigate('chargeback', 'Cloud Intelligence', 'Chargeback')


@pytest.fixture
def intel_reports_pg():
    return navigate('reports', 'Cloud Intelligence', 'Reports')
