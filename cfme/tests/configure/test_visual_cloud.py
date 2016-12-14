# -*- coding: utf-8 -*-
import pytest

from cfme import login
from cfme import test_requirements
from cfme.configure.settings import visual
from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.provider import CloudProvider
from cfme.cloud.flavor import Flavor
from cfme.cloud.instance import Instance
from cfme.cloud.keypairs import KeyPair
from cfme.cloud.stack import Stack
from cfme.cloud.tenant import Tenant
from cfme.cloud.volume import Volume
from cfme.web_ui import paginator, toolbar as tb, match_location
from utils.appliance.implementations.ui import navigate_to
from utils.providers import setup_a_provider as _setup_a_provider
from utils import version

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]

grid_pages = version.pick({
    version.LOWEST: [CloudProvider,
                     AvailabilityZone,
                     Tenant,
                     Volume,
                     Flavor,
                     Instance,
                     Stack,
                     KeyPair],
    # Volume was removed in 5.7
    '5.7': [CloudProvider,
            AvailabilityZone,
            Tenant,
            Flavor,
            Instance,
            Stack,
            KeyPair]
})

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


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="cloud", prov_type="openstack", validate=True, check_existing=True)


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
def test_grid_page_per_item(request, setup_a_provider, page, set_grid):
    """ Tests grid items per page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.grid_view_limit
    navigate_to(page, 'All')
    tb.select('Grid View')
    if paginator.rec_total() is not None:
        if int(paginator.rec_total()) >= int(limit):
            assert int(paginator.rec_end()) == int(limit), \
                "Gridview Failed for page {}!".format(page)


@pytest.mark.parametrize('page', grid_pages, scope="module")
def test_tile_page_per_item(request, setup_a_provider, page, set_tile):
    """ Tests tile items per page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.tile_view_limit
    navigate_to(page, 'All')
    tb.select('Tile View')
    if paginator.rec_total() is not None:
        if int(paginator.rec_total()) >= int(limit):
            assert int(paginator.rec_end()) == int(limit), \
                "Tileview Failed for page {}!".format(page)


@pytest.mark.parametrize('page', grid_pages, scope="module")
def test_list_page_per_item(request, setup_a_provider, page, set_list):
    """ Tests list items per page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.list_view_limit
    navigate_to(page, 'All')
    tb.select('List View')
    if paginator.rec_total() is not None:
        if int(paginator.rec_total()) >= int(limit):
            assert int(paginator.rec_end()) == int(limit), \
                "Listview Failed for page {}!".format(page)


@pytest.mark.parametrize('start_page', landing_pages, scope="module")
def test_start_page(request, setup_a_provider, start_page):
    """ Tests start page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(set_default_page)
    visual.login_page = start_page
    login.logout()
    login.login_admin()
    match_args = landing_pages[start_page]
    assert match_location(**match_args), "Landing Page Failed"


def test_cloudprovider_noquads(request, setup_a_provider, set_cloud_provider_quad):
    navigate_to(CloudProvider, 'All')
    assert visual.check_image_exists, "Image View Failed!"
