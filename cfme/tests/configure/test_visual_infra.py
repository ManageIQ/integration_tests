# -*- coding: utf-8 -*-

import pytest
import re
from cfme import login
from cfme.configure.settings import visual
from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.reports import CannedSavedReport
from cfme.web_ui import paginator, toolbar as tb, menu
from utils.conf import cfme_data
from utils.providers import setup_a_provider as _setup_a_provider

try:
    grid_pages = cfme_data.grid_pages.infra
except KeyError:
    grid_pages = []
grid_uncollectif = pytest.mark.uncollectif(not grid_pages, reason='no grid pages configured')

try:
    landing_pages = cfme_data.landing_pages.infra
except KeyError:
    landing_pages = []
landing_uncollectif = pytest.mark.uncollectif(not grid_pages, reason='no landing pages configured')


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="infra", validate=True, check_existing=True)


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


@pytest.yield_fixture(scope="module")
def set_report():
    reportlimit = visual.report_view_limit
    visual.report_view_limit = 5
    yield
    visual.report_view_limit = reportlimit


def set_default_page():
    visual.set_login_page = "Cloud Intelligence / Dashboard"


def go_to_grid(page):
    sel.force_navigate(page)
    tb.select('Grid View')


@pytest.yield_fixture(scope="module")
def set_infra_provider_quad():
    visual.infra_provider_quad = False
    yield
    visual.infra_provider_quad = True


@pytest.yield_fixture(scope="module")
def set_host_quad():
    visual.host_quad = False
    yield
    visual.host_quad = True


@pytest.yield_fixture(scope="module")
def set_datastore_quad():
    visual.datastore_quad = False
    yield
    visual.datastore_quad = True


@pytest.yield_fixture(scope="module")
def set_vm_quad():
    visual.vm_quad = False
    yield
    visual.vm_quad = True


@pytest.yield_fixture(scope="module")
def set_template_quad():
    visual.template_quad = False
    yield
    visual.template_quad = True


@grid_uncollectif
@pytest.mark.meta(blockers=[1267148])
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
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Gridview Failed for page {}!".format(page)


@grid_uncollectif
@pytest.mark.meta(blockers=[1267148])
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
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Tileview Failed for page {}!".format(page)


@grid_uncollectif
@pytest.mark.meta(blockers=[1267148])
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
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Listview Failed for page {}!".format(page)


@pytest.mark.meta(blockers=[1267148])
def test_report_page_per_item(setup_a_provider, set_report):
    """ Tests report items per page

    Metadata:
        test_flag: visuals
    """
    path = ["Configuration Management", "Virtual Machines", "VMs Snapshot Summary"]
    limit = visual.report_view_limit
    report = CannedSavedReport.new(path)
    report.navigate()
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Reportview Failed!"


@landing_uncollectif
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
    assert menu.is_page_active(level[0].strip(), level[1].strip()), "Landing Page Failed"


def test_infraprovider_noquads(request, setup_a_provider, set_infra_provider_quad):
    sel.force_navigate('infrastructure_providers')
    assert visual.check_image_exists, "Image View Failed!"


def test_host_noquads(request, setup_a_provider, set_host_quad):
    sel.force_navigate('infrastructure_hosts')
    assert visual.check_image_exists, "Image View Failed!"


def test_datastore_noquads(request, setup_a_provider, set_datastore_quad):
    sel.force_navigate('infrastructure_datastores')
    assert visual.check_image_exists, "Image View Failed!"


def test_vm_noquads(request, setup_a_provider, set_vm_quad):
    sel.force_navigate('infrastructure_virtual_machines')
    assert visual.check_image_exists, "Image View Failed!"


def test_template_noquads(request, setup_a_provider, set_template_quad):
    sel.force_navigate('infra_templates')
    assert visual.check_image_exists, "Image View Failed!"
