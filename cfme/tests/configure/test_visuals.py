# -*- coding: utf-8 -*-

import pytest
from cfme.configure.settings import visual
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import paginator, toolbar as tb
from utils import testgen
from utils.conf import cfme_data
from utils.providers import setup_provider


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(metafunc, ['virtualcenter'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture()
def provider_init(provider_key):
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="module")
def set_grid():
    visual.grid_view_limit = 5


@pytest.fixture(scope="module")
def set_tile():
    visual.tile_view_limit = 5


@pytest.fixture(scope="module")
def set_list():
    visual.list_view_limit = 5


def go_to_grid(page):
    sel.force_navigate(page)
    tb.select('Grid View')


@pytest.mark.parametrize('page', cfme_data.get('grid_pages'), scope="module")
def test_grid_page_per_item(request, provider_init, page, set_grid):
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.grid_view_limit
    sel.force_navigate(page)
    tb.select('Grid View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Gridview Failed for page {}!".format(page)


@pytest.mark.parametrize('page', cfme_data.get('grid_pages'), scope="module")
def test_tile_page_per_item(request, provider_init, page, set_tile):
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.tile_view_limit
    sel.force_navigate(page)
    tb.select('Tile View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Tileview Failed for page {}!".format(page)


@pytest.mark.parametrize('page', cfme_data.get('grid_pages'), scope="module")
def test_list_page_per_item(request, provider_init, page, set_list):
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.list_view_limit
    sel.force_navigate(page)
    tb.select('List View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Listview Failed for page {}!".format(page)
