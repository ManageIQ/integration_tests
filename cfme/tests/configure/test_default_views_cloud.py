# -*- coding: utf-8 -*-
import pytest
from six import string_types

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('openstack_provider')]

gtl_params = {
    'Cloud Providers': CloudProvider,
    'Availability Zones': 'cloud_av_zones',
    'Flavors': 'cloud_flavors',
    'Instances': 'cloud_instances',
    'Images': 'cloud_images'
}


# TODO refactor for setup_provider parametrization with new 'latest' tag


def set_and_test_default_view(appliance, group_name, expected_view, page):
    default_views = appliance.user.my_settings.default_views
    old_default = default_views.get_default_view(group_name, fieldset='Clouds')
    default_views.set_default_view(group_name, expected_view, fieldset='Clouds')
    # gtl_params.values(), source of page, are mix of class and collection name
    nav_cls = getattr(appliance.collections, page) if isinstance(page, string_types) else page
    selected_view = navigate_to(nav_cls, 'All', use_resetter=False).toolbar.view_selector.selected
    assert expected_view == selected_view, '{} view setting failed'.format(expected_view)
    default_views.set_default_view(group_name, old_default, fieldset='Clouds')


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_cloud_tile_defaultview(appliance, request, key):
    set_and_test_default_view(appliance, key, 'Tile View', gtl_params[key])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_cloud_list_defaultview(appliance, request, key):
    set_and_test_default_view(appliance, key, 'List View', gtl_params[key])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_cloud_grid_defaultview(appliance, request, key):
    set_and_test_default_view(appliance, key, 'Grid View', gtl_params[key])


def set_and_test_compare_view(appliance, group_name, expected_view, selector_type='views_selector'):
    default_views = appliance.user.my_settings.default_views
    old_default = default_views.get_default_view(group_name)
    default_views.set_default_view(group_name, expected_view)
    inst_view = navigate_to(appliance.collections.cloud_instances, 'All')
    [e.check() for e in inst_view.entities.get_all()[:2]]
    inst_view.toolbar.configuration.item_select('Compare Selected items')
    selected_view = getattr(inst_view.actions, selector_type).selected
    assert expected_view == selected_view, '{} setting failed'.format(expected_view)
    default_views.set_default_view(group_name, old_default)


def test_cloud_expanded_view(appliance, request):
    set_and_test_compare_view(appliance, 'Compare', 'Expanded View')


def test_cloud_compressed_view(appliance, request):
    set_and_test_compare_view(appliance, 'Compare', 'Compressed View')


def test_cloud_details_mode(appliance, request):
    set_and_test_compare_view(appliance, 'Compare Mode', 'Details Mode', 'modes_selector')


def test_cloud_exists_mode(appliance, request):
    set_and_test_compare_view(appliance, 'Compare Mode', 'Exists Mode', 'modes_selector')
