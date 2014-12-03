# -*- coding: utf-8 -*-


import cfme.configure.settings as st
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import paginator, toolbar as tb
from utils.conf import cfme_data


def test_grid_page_per_item(soft_assert):
    ns = st.Visual(grid_view='5',
                   tile_view=None,
                   list_view=None)
    ns.updatesettings()
    for page in cfme_data['grid_pages']:
        sel.force_navigate(page)
        if paginator.rec_total() >= ns.grid_view:
            soft_assert(int(paginator.rec_end()) == int(ns.grid_view), "Gridview Failed!")
        else:
            continue


def test_tile_page_per_item(soft_assert):
    ns = st.Visual(grid_view=None,
                   tile_view='5',
                   list_view=None)
    ns.updatesettings()
    for page in cfme_data['grid_pages']:
        sel.force_navigate(page)
        tb.select('Tile View')
        if paginator.rec_total() >= ns.tile_view:
            soft_assert(int(paginator.rec_end()) == int(ns.tile_view), "Tileview Failed!")
        else:
            continue


def test_list_page_per_item(soft_assert):
    ns = st.Visual(grid_view=None,
                   tile_view=None,
                   list_view='5')
    ns.updatesettings()
    for page in cfme_data['grid_pages']:
        sel.force_navigate(page)
        tb.select('List View')
        if paginator.rec_total() >= ns.list_view:
                soft_assert(int(paginator.rec_end()) == int(ns.list_view), "Listview Failed!")
        else:
            continue
