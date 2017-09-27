# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.flavor import Flavor
from cfme.cloud.instance import Instance
from cfme.cloud.instance.image import Image
from cfme.configure.settings import DefaultView
from cfme.web_ui import toolbar as tb
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('openstack_provider')]

gtl_params = {
    'Cloud Providers': CloudProvider,
    'Availability Zones': AvailabilityZone,
    'Flavors': Flavor,
    'Instances': Instance,
    'Images': Image
}


# TODO refactor for setup_provider parametrization with new 'latest' tag


def set_and_test_default_view(group_name, view, page):
    old_default = DefaultView.get_default_view(group_name, fieldset='Clouds')
    DefaultView.set_default_view(group_name, view, fieldset='Clouds')
    navigate_to(page, 'All', use_resetter=False)
    # TODO replace view detection with widgets when all tested classes have them
    assert tb.is_active(view), "{} view setting failed".format(view)
    DefaultView.set_default_view(group_name, old_default, fieldset='Clouds')

# BZ 1283118 written against 5.5 has a mix of what default views do and don't work on different
# pages in different releases


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_cloud_tile_defaultview(request, key):
    set_and_test_default_view(key, 'Tile View', gtl_params[key])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_cloud_list_defaultview(request, key):
    set_and_test_default_view(key, 'List View', gtl_params[key])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_cloud_grid_defaultview(request, key):
    set_and_test_default_view(key, 'Grid View', gtl_params[key])


def set_and_test_view(group_name, view):
    old_default = DefaultView.get_default_view(group_name)
    DefaultView.set_default_view(group_name, view)
    inst_view = navigate_to(Instance, 'All')
    [e.check() for e in inst_view.entities.get_all()[:2]]
    inst_view.toolbar.configuration.item_select('Compare Selected items')
    assert tb.is_active(view), "{} setting failed".format(view)
    DefaultView.set_default_view(group_name, old_default)


def test_cloud_expanded_view(request):
    set_and_test_view('Compare', 'Expanded View')


def test_cloud_compressed_view(request):
    set_and_test_view('Compare', 'Compressed View')


def test_cloud_details_view(request):
    set_and_test_view('Compare Mode', 'Details Mode')


def test_cloud_exists_view(request):
    set_and_test_view('Compare Mode', 'Exists Mode')
