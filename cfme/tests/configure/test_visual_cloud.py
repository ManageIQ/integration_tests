# -*- coding: utf-8 -*-
import pytest


from cfme import test_requirements
from cfme.configure.settings import visual
from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.provider import CloudProvider
from cfme.cloud.flavor import Flavor
from cfme.cloud.instance import Instance
from cfme.cloud.keypairs import KeyPairCollection
from cfme.cloud.stack import StackCollection
from cfme.cloud.tenant import TenantCollection
from cfme.web_ui import toolbar as tb, match_location
from cfme.utils.appliance import BaseCollection
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures("openstack_provider")]

# TODO When all of these classes have widgets and views use them in the tests
grid_pages = [CloudProvider,
              AvailabilityZone,
              TenantCollection,
              Flavor,
              Instance,
              StackCollection,
              KeyPairCollection]

# Dict values are kwargs for cfme.web_ui.match_location

landing_pages = {
    'Clouds / Providers': {'controller': 'ems_cloud',
                           'title': 'Cloud Providers',
                           'summary': 'Cloud Providers'},
    'Clouds / Key Pairs': {'controller': 'auth_key_pair_cloud',
                           'title': 'Key Pairs',
                           'summary': 'Key Pairs'},
    'Clouds / Tenants': {'controller': 'cloud_tenant',
                         'title': 'Cloud Tenants',
                         'summary': 'Cloud Tenants'},
    'Clouds / Flavors': {'controller': 'flavor',
                         'title': 'Flavors',
                         'summary': 'Flavors'},
    'Clouds / Availability Zones': {'controller': 'availability_zone',
                                    'title': 'Availability Zones',
                                    'summary': 'Availability Zones'},
}


@pytest.yield_fixture(scope="module")
def set_grid():
    gridlimit = visual.grid_view_limit
    visual.grid_view_limit = 5
    yield
    visual.grid_view_limit = gridlimit


@pytest.yield_fixture(scope="module")
def set_tile():
    tilelimit = visual.tile_view_limit
    visual.tile_view_limit = 5
    yield
    visual.tile_view_limit = tilelimit


@pytest.yield_fixture(scope="module")
def set_list():
    listlimit = visual.list_view_limit
    visual.list_view_limit = 5
    yield
    visual.list_view_limit = listlimit


def set_default_page():
    visual.set_login_page = "Cloud Intelligence / Dashboard"


def go_to_grid(page):
    navigate_to(page, 'All')
    tb.select('Grid View')


@pytest.yield_fixture(scope="module")
def set_cloud_provider_quad():
    visual.cloud_provider_quad = False
    yield
    visual.cloud_provider_quad = True


@pytest.mark.parametrize('page', grid_pages, scope="module")
def test_cloud_grid_page_per_item(request, page, set_grid, appliance):
    """ Tests grid items per page

    Metadata:
        test_flag: visuals
    """
    if issubclass(page, BaseCollection):
        page = page(appliance)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.grid_view_limit
    navigate_to(page, 'All')
    tb.select('Grid View')
    from cfme.web_ui import paginator
    if paginator.rec_total() is not None:
        if int(paginator.rec_total()) >= int(limit):
            assert int(paginator.rec_end()) == int(limit), \
                "Gridview Failed for page {}!".format(page)


@pytest.mark.parametrize('page', grid_pages, scope="module")
def test_cloud_tile_page_per_item(request, page, set_tile, appliance):
    """ Tests tile items per page

    Metadata:
        test_flag: visuals
    """
    if issubclass(page, BaseCollection):
        page = page(appliance)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.tile_view_limit
    navigate_to(page, 'All')
    tb.select('Tile View')
    from cfme.web_ui import paginator
    if paginator.rec_total() is not None:
        if int(paginator.rec_total()) >= int(limit):
            assert int(paginator.rec_end()) == int(limit), \
                "Tileview Failed for page {}!".format(page)


@pytest.mark.parametrize('page', grid_pages, scope="module")
def test_cloud_list_page_per_item(request, page, set_list, appliance):
    """ Tests list items per page

    Metadata:
        test_flag: visuals
    """
    if issubclass(page, BaseCollection):
        page = page(appliance)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.list_view_limit
    navigate_to(page, 'All')
    tb.select('List View')
    from cfme.web_ui import paginator
    if paginator.rec_total() is not None:
        if int(paginator.rec_total()) >= int(limit):
            assert int(paginator.rec_end()) == int(limit), \
                "Listview Failed for page {}!".format(page)


@pytest.mark.parametrize('start_page', landing_pages, scope="module")
def test_cloud_start_page(request, appliance, start_page):
    # TODO: Need to dynamically fetch this value and move this test case to common.
    """ Tests start page

    Metadata:
        test_flag: visuals
    """
    start = "" if appliance.version < '5.8' else "Compute / "
    start_page = "{}{}".format(start, start_page)
    request.addfinalizer(set_default_page)
    visual.login_page = start_page
    appliance.server.logout()
    appliance.server.login_admin()
    logged_in_page = navigate_to(appliance.server, 'LoggedIn')
    assert logged_in_page.is_displayed


def test_cloudprovider_noquads(request, set_cloud_provider_quad):
    view = navigate_to(CloudProvider, 'All')
    view.toolbar.view_selector.select("Grid View")
    # Here get_first_entity() method will return None when the Quadrants option is deactivated.
    assert view.entities.get_first_entity().data is None
