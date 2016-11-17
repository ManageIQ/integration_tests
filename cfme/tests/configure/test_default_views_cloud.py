# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.configure.settings import DefaultView
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Quadicon, fill, toolbar as tb
from utils.appliance.implementations.ui import navigate_to
from utils.providers import setup_a_provider as _setup_a_provider

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('setup_a_provider')]

gtl_params = {
    'Cloud Providers': CloudProvider,
    'Availability Zones': 'clouds_availability_zones',
    'Flavors': 'clouds_flavors',
    'Instances': 'clouds_instances',
    # clouds_images DNE, replace with proper object with navmazing destinations
    # 'Images': 'clouds_images'
}


# TODO refactor for setup_provider parametrization with new 'latest' tag
@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="cloud", prov_type="openstack", validate=True, check_existing=True)


def select_two_quads():
    count = 0
    for quad in Quadicon.all("cloud_prov", this_page=True):
        count += 1
        if count > 2:
            break
        fill(quad.checkbox(), True)


def set_and_test_default_view(group_name, view, page):
    old_default = DefaultView.get_default_view(group_name)
    DefaultView.set_default_view(group_name, view)
    if isinstance(page, basestring):
        sel.force_navigate(page)
    else:
        navigate_to(page, 'All', use_resetter=False)
    assert tb.is_active(view), "{} view setting failed".format(view)
    DefaultView.set_default_view(group_name, old_default)

# BZ 1283118 written against 5.5 has a mix of what default views do and don't work on different
# pages in different releases


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_tile_defaultview(request, key):
    set_and_test_default_view(key, 'Tile View', gtl_params[key])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_list_defaultview(request, key):
    set_and_test_default_view(key, 'List View', gtl_params[key])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_grid_defaultview(request, key):
    set_and_test_default_view(key, 'Grid View', gtl_params[key])


def set_and_test_view(group_name, view):
    old_default = DefaultView.get_default_view(group_name)
    DefaultView.set_default_view(group_name, view)
    sel.force_navigate('clouds_instances')
    select_two_quads()
    tb.select('Configuration', 'Compare Selected items')
    assert tb.is_active(view), "{} setting failed".format(view)
    DefaultView.set_default_view(group_name, old_default)


@pytest.mark.meta(blockers=[1394331])
def test_expanded_view(request):
    set_and_test_view('Compare', 'Expanded View')


@pytest.mark.meta(blockers=[1394331])
def test_compressed_view(request):
    set_and_test_view('Compare', 'Compressed View')


@pytest.mark.meta(blockers=[1394331])
def test_details_view(request):
    set_and_test_view('Compare Mode', 'Details Mode')


@pytest.mark.meta(blockers=[1394331])
def test_exists_view(request):
    set_and_test_view('Compare Mode', 'Exists Mode')
