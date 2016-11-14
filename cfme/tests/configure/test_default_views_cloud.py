# -*- coding: utf-8 -*-

import pytest
import re
from cfme import test_requirements
from cfme.fixtures import pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from cfme.web_ui import ButtonGroup, form_buttons, Quadicon, fill
from utils.providers import setup_a_provider as _setup_a_provider
from cfme.configure import settings  # NOQA
from cfme.cloud import instance  # NOQA

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]


gtl_params = [
    'Cloud Providers/clouds_providers',
    'Availability Zones/clouds_availability_zones',
    'Flavors/clouds_flavors',
    'Instances/clouds_instances',
    'Images/clouds_images'
]

gtl_parametrize = pytest.mark.parametrize('key', gtl_params, scope="module")


def select_two_quads():
    count = 0
    for quad in Quadicon.all("cloud_prov", this_page=True):
        count += 1
        if count > 2:
            break
        fill(quad.checkbox(), True)


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="cloud", validate=True, check_existing=True)


def set_view(group, button):
    bg = ButtonGroup(group)
    if bg.active != button:
        bg.choose(button)
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
    checkbox = ("(.//input[@id='listcheckbox'])[2]")
    sel.check(checkbox)


def set_and_test_default_view(group_name, view, page):
    default_view = get_default_view(group_name)
    set_view(group_name, view)
    sel.force_navigate(page)
    assert tb.is_active(view), "{} view setting failed".format(view)
    reset_default_view(group_name, default_view)


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_tile_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    set_and_test_default_view(name[0], 'Tile View', name[1])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_list_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    set_and_test_default_view(name[0], 'List View', name[1])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_grid_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    set_and_test_default_view(name[0], 'Grid View', name[1])


def set_and_test_view(group_name, view):
    default_view = get_default_view(group_name)
    set_view(group_name, view)
    sel.force_navigate('clouds_instances')
    select_two_quads()
    tb.select('Configuration', 'Compare Selected items')
    assert tb.is_active(view), "{} setting failed".format(view)
    reset_default_view(group_name, default_view)


def test_expanded_view(request, setup_a_provider):
    set_and_test_view('Compare', 'Expanded View')


def test_compressed_view(request, setup_a_provider):
    set_and_test_view('Compare', 'Compressed View')


def test_details_view(request, setup_a_provider):
    set_and_test_view('Compare Mode', 'Details Mode')


def test_exists_view(request, setup_a_provider):
    set_and_test_view('Compare Mode', 'Exists Mode')
