# -*- coding: utf-8 -*-

import pytest
import re
from cfme.fixtures import pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from cfme.web_ui import ButtonGroup, form_buttons
from utils.conf import cfme_data
from utils.providers import setup_a_provider as _setup_a_provider
from cfme.configure import settings  # NOQA


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="infra", validate=True, check_existing=True)


def set_tile_view(name):
    bg = ButtonGroup(name)
    bg.choose('Tile View')
    sel.click(form_buttons.save)


def set_list_view(name):
    bg = ButtonGroup(name)
    bg.choose('List View')
    sel.click(form_buttons.save)


def set_grid_view(name):
    bg = ButtonGroup(name)
    bg.choose('Grid View')
    sel.click(form_buttons.save)


def reset_default_view(name, default_view):
    bg = ButtonGroup(name)
    sel.force_navigate("my_settings_default_views")
    bg.choose(default_view)
    sel.click(form_buttons.save)


def get_default_view(name):
    bg = ButtonGroup(name)
    pytest.sel.force_navigate("my_settings_default_views")
    default_view = bg.active
    return default_view


@pytest.mark.parametrize('key', cfme_data.get('defaultview_data', []), scope="module")
def test_tile_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_tile_view(name[0])
    sel.force_navigate(name[1])
    assert tb.is_vms_tile_view(), "Default view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.parametrize('key', cfme_data.get('defaultview_data', []), scope="module")
def test_list_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_list_view(name[0])
    sel.force_navigate(name[1])
    assert tb.is_vms_list_view(), "Default view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.parametrize('key', cfme_data.get('defaultview_data', []), scope="module")
def test_grid_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_grid_view(name[0])
    sel.force_navigate(name[1])
    assert tb.is_vms_grid_view(), "Default view setting failed"
    reset_default_view(name[0], default_view)
