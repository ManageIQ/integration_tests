# -*- coding: utf-8 -*-

import pytest
import re
from cfme.fixtures import pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from cfme.web_ui import ButtonGroup, form_buttons
from utils.conf import cfme_data
from utils.providers import setup_a_provider as _setup_a_provider
from utils import version
from cfme.configure import settings  # NOQA
from cfme.cloud import instance  # NOQA


def minimise_dict(item):
    if isinstance(item, dict):
        return version.pick({str(k): v for k, v in item.iteritems()})
    else:
        return item

try:
    gtl_params = cfme_data['defaultview_data']['gtl']['cloud']
    gtl_params = [minimise_dict(item) for item in gtl_params]
except KeyError:
    gtl_params = []
finally:
    gtl_parametrize = pytest.mark.parametrize('key', gtl_params, scope="module")


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="cloud", validate=True, check_existing=True)


def set_tile_view(name):
    bg = ButtonGroup(name)
    if bg.active != 'Tile View':
        bg.choose('Tile View')
        sel.click(form_buttons.save)


def set_list_view(name):
    bg = ButtonGroup(name)
    if bg.active != 'List View':
        bg.choose('List View')
        sel.click(form_buttons.save)


def set_grid_view(name):
    bg = ButtonGroup(name)
    if bg.active != 'Grid View':
        bg.choose('Grid View')
        sel.click(form_buttons.save)


def set_expanded_view(name):
    bg = ButtonGroup(name)
    if bg.active != 'Expanded View':
        bg.choose('Expanded View')
        sel.click(form_buttons.save)


def set_compressed_view(name):
    bg = ButtonGroup(name)
    if bg.active != 'Compressed View':
        bg.choose('Compressed View')
        sel.click(form_buttons.save)


def reset_default_view(name, default_view):
    bg = ButtonGroup(name)
    sel.force_navigate("my_settings_default_views")
    if bg.active != default_view:
        bg.choose(default_view)
        sel.click(form_buttons.save)


def get_default_view(name):
    bg = ButtonGroup(name)
    pytest.sel.force_navigate("my_settings_default_views")
    default_view = bg.active
    return default_view


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_tile_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_tile_view(name[0])
    sel.force_navigate(name[1])
    assert tb.is_vms_tile_view(), "Tile Default view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_list_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_list_view(name[0])
    sel.force_navigate(name[1])
    assert tb.is_vms_list_view(), "List Default view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_grid_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_grid_view(name[0])
    sel.force_navigate(name[1])
    assert tb.is_vms_grid_view(), "Grid Default view setting failed"
    reset_default_view(name[0], default_view)
