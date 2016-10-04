# -*- coding: utf-8 -*-

import pytest
import re
from cfme.fixtures import pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from cfme.web_ui import ButtonGroup, form_buttons, Quadicon
from utils import version
from utils.providers import setup_a_provider as _setup_a_provider
from cfme.configure import settings  # NOQA
from cfme.cloud import instance  # NOQA

pytestmark = [pytest.mark.tier(3)]


gtl_params = [
    'Cloud Providers/clouds_providers',
    'Availability Zones/clouds_availability_zones',
    'Flavors/clouds_flavors',
    'Instances/clouds_instances',
    'Images/clouds_images'
]
exp_comp_params = [
    'Compare/clouds_instances/Configuration/Compare Selected items'
]

gtl_parametrize = pytest.mark.parametrize('key', gtl_params, scope="module")
exp_comp_parametrize = pytest.mark.parametrize('key', exp_comp_params, scope="module")


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


def set_details_view(name):
    bg = ButtonGroup(name)
    if bg.active != 'Details Mode':
        bg.choose('Details Mode')
        sel.click(form_buttons.save)


def set_exist_view(name):
    bg = ButtonGroup(name)
    if bg.active != 'Exists Mode':
        bg.choose('Exists Mode')
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


def select_second_quad():
    checkbox = version.pick({version.LOWEST: "(.//input[@id='listcheckbox'])[2]",
                            "5.7": "//div[2]/table/tbody/tr/td/input"})
    sel.check(checkbox)


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_tile_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_tile_view(name[0])
    sel.force_navigate(name[1])
    if name[1] == "clouds_providers" or "clouds_instances":
        tb.select('Tile View')
    assert tb.is_active('Tile View'), "Tile Default view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_list_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_list_view(name[0])
    sel.force_navigate(name[1])
    if name[1] == "clouds_providers" or "clouds_instances":
        tb.select('List View')
    assert tb.is_active('List View'), "List Default view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_grid_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_grid_view(name[0])
    sel.force_navigate(name[1])
    assert tb.is_active('Grid View'), "Grid Default view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.meta(blockers=[1381209])
@pytest.mark.parametrize('key', exp_comp_params, scope="module")
def test_expanded_view(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_expanded_view(name[0])
    sel.force_navigate(name[1])
    Quadicon.select_first_quad()
    select_second_quad()
    tb.select(name[2], name[3])
    assert tb.is_active('Expanded View'), "Expanded view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.meta(blockers=[1381209])
@pytest.mark.parametrize('key', exp_comp_params, scope="module")
def test_compressed_view(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_compressed_view(name[0])
    sel.force_navigate(name[1])
    Quadicon.select_first_quad()
    select_second_quad()
    tb.select(name[2], name[3])
    assert tb.is_active('Compressed View'), "Compressed view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.meta(blockers=[1381209])
@pytest.mark.parametrize('key', exp_comp_params, scope="module")
def test_details_view(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    button_name = name[0] + " Mode"
    default_view = get_default_view(button_name)
    set_details_view(button_name)
    sel.force_navigate(name[1])
    Quadicon.select_first_quad()
    select_second_quad()
    tb.select(name[2], name[3])
    assert tb.is_active('Details Mode'), "Details view setting failed"
    reset_default_view(button_name, default_view)


@pytest.mark.meta(blockers=[1381209])
@pytest.mark.parametrize('key', exp_comp_params, scope="module")
def test_exists_view(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    button_name = name[0] + " Mode"
    default_view = get_default_view(button_name)
    set_exist_view(button_name)
    sel.force_navigate(name[1])
    Quadicon.select_first_quad()
    select_second_quad()
    tb.select(name[2], name[3])
    assert tb.is_active('Exists Mode'), "Exists view setting failed"
    reset_default_view(button_name, default_view)
