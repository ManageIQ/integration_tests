# -*- coding: utf-8 -*-


import pytest
import re
from cfme import login
from cfme.configure.settings import visual
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import paginator, toolbar as tb, menu
from utils.providers import setup_a_provider as _setup_a_provider

pytestmark = [pytest.mark.tier(3)]

grid_pages = [
    'clouds_providers',
    'clouds_availability_zones',
    'clouds_tenants',
    'clouds_volumes',
    'clouds_flavors',
    'clouds_instances',
    'clouds_stacks',
    'clouds_key_pairs',
    'clouds_object_stores',
]

landing_pages = [
    'Clouds / Providers',
    'Clouds / Key Pairs',
    'Clouds / Availability Zones',
    'Clouds / Tenants',
    'Clouds / Flavors',
]


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
    sel.force_navigate(page)
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
    sel.force_navigate(page)
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
    sel.force_navigate(page)
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
    sel.force_navigate(page)
    tb.select('List View')
    if paginator.rec_total() is not None:
        if int(paginator.rec_total()) >= int(limit):
            assert int(paginator.rec_end()) == int(limit), \
                "Listview Failed for page {}!".format(page)


@pytest.mark.meta(blockers=[1267148])
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
    level = re.split(r"\/", start_page)
    assert menu.nav.is_page_active(None, level[0].strip(), level[1].strip()), "Landing Page Failed"


def test_cloudprovider_noquads(request, setup_a_provider, set_cloud_provider_quad):
    sel.force_navigate('clouds_providers')
    assert visual.check_image_exists, "Image View Failed!"
