# -*- coding: utf-8 -*-

import pytest
import re
from cfme.fixtures import pytest_selenium as sel
from cfme import test_requirements
import cfme.web_ui.toolbar as tb
from cfme.web_ui import ButtonGroup, form_buttons, Quadicon
from utils.providers import setup_a_provider as _setup_a_provider
from utils import version
from cfme.configure import settings  # NOQA
from cfme.services.catalogs import catalog_item  # NOQA
from cfme.services import workloads  # NOQA
from cfme.intelligence.reports.reports import CannedSavedReport

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]


def minimise_dict(item):
    if isinstance(item, dict):
        return version.pick({str(k): v for k, v in item.iteritems()})
    else:
        return item

# todo: infrastructure hosts, pools, stores, clusters are removed due to changing navigation
#  to navmazing. all items have to be put back once navigation change is fully done

gtl_params = [
    'Infrastructure Providers/infrastructure_providers',
    'VMs/infra_vms',
    'My Services/my_services',
    'Catalog Items/catalog_items',
    'VMs & Instances/service_vms_instances',
    'Templates & Images/service_templates_images'
]
exp_comp_params = [
    'Compare/infrastructure_virtual_machines/Configuration/Compare Selected items'
]
exp_comp_params = [minimise_dict(item) for item in exp_comp_params]

gtl_parametrize = pytest.mark.parametrize('key', gtl_params, scope="module")
exp_comp_parametrize = pytest.mark.parametrize('key', exp_comp_params, scope="module")


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="infra", validate=True, check_existing=True)


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
    checkbox = ("(.//input[@id='listcheckbox'])[2]")
    sel.check(checkbox)


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_tile_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_tile_view(name[0])
    sel.force_navigate(name[1])
    if name[1] == "infrastructure_providers":
        tb.select('Tile View')
    assert tb.is_active('Tile View'), "Tile Default view setting failed"
    reset_default_view(name[0], default_view)


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_list_defaultview(request, setup_a_provider, key):
    name = re.split(r"\/", key)
    default_view = get_default_view(name[0])
    set_list_view(name[0])
    sel.force_navigate(name[1])
    if name[1] == "infrastructure_providers":
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


def test_hybrid_view(request, setup_a_provider):
    path = ["Configuration Management", "Hosts", "Virtual Infrastructure Platforms"]
    report = CannedSavedReport.new(path)
    report.navigate()
    tb.select('Hybrid View')
    assert tb.is_active('Hybrid View'), "Hybrid view setting failed"


def test_graph_view(request, setup_a_provider):
    path = ["Configuration Management", "Hosts", "Virtual Infrastructure Platforms"]
    report = CannedSavedReport.new(path)
    report.navigate()
    tb.select('Graph View')
    assert tb.is_active('Graph View'), "Graph view setting failed"


def test_tabular_view(request, setup_a_provider):
    path = ["Configuration Management", "Hosts", "Virtual Infrastructure Platforms"]
    report = CannedSavedReport.new(path)
    report.navigate()
    tb.select('Tabular View')
    assert tb.is_active('Tabular View'), "Tabular view setting failed"
