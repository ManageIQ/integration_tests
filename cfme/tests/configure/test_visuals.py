# -*- coding: utf-8 -*-

import pytest
import re
from cfme import login
from cfme.configure.settings import visual
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import paginator, toolbar as tb, menu
from utils.conf import cfme_data
from utils.providers import setup_a_provider


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider(prov_class="infra", validate=True, check_existing=True)


@pytest.yield_fixture(scope="module")
def set_grid():
    visual.grid_view_limit = 5
    yield
    visual.grid_view_limit = 20


@pytest.yield_fixture(scope="module")
def set_tile():
    visual.tile_view_limit = 5
    yield
    visual.tile_view_limit = 20


@pytest.yield_fixture(scope="module")
def set_list():
    visual.list_view_limit = 5
    yield
    visual.list_view_limit = 20


def set_default_page():
    visual.set_login_page = "Cloud Intelligence / Dashboard"


def go_to_grid(page):
    sel.force_navigate(page)
    tb.select('Grid View')


@pytest.mark.parametrize('page', cfme_data.get('grid_pages'), scope="module")
def test_grid_page_per_item(request, setup_first_provider, page, set_grid):
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.grid_view_limit
    sel.force_navigate(page)
    tb.select('Grid View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Gridview Failed for page {}!".format(page)


@pytest.mark.parametrize('page', cfme_data.get('grid_pages'), scope="module")
def test_tile_page_per_item(request, setup_first_provider, page, set_tile):
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.tile_view_limit
    sel.force_navigate(page)
    tb.select('Tile View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Tileview Failed for page {}!".format(page)


@pytest.mark.parametrize('page', cfme_data.get('grid_pages'), scope="module")
def test_list_page_per_item(request, setup_first_provider, page, set_list):
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.list_view_limit
    sel.force_navigate(page)
    tb.select('List View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Listview Failed for page {}!".format(page)


@pytest.mark.parametrize('start_page', cfme_data.get('landing_pages'), scope="module")
def test_start_page(request, setup_first_provider, start_page):
    request.addfinalizer(set_default_page)
    visual.login_page = start_page
    login.logout()
    login.login_admin()
    level = re.split(r"\/", start_page)
    assert menu.is_page_active(level[0].strip(), level[1].strip()), "Landing Page Failed"
