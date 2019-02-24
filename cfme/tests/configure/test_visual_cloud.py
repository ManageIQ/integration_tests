# -*- coding: utf-8 -*-
import pytest
import six

from cfme import test_requirements
from cfme.cloud.availability_zone import AvailabilityZoneAllView
from cfme.cloud.flavor import FlavorAllView
from cfme.cloud.keypairs import KeyPairAllView
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider import CloudProvidersView
from cfme.cloud.stack import StackAllView
from cfme.cloud.tenant import TenantAllView
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('openstack_provider')]

# Dict values are views which are required to check correct landing pages.
landing_pages = {
    'Compute / Clouds / Providers': CloudProvidersView,
    'Compute / Clouds / Key Pairs': KeyPairAllView,
    'Compute / Clouds / Tenants': TenantAllView,
    'Compute / Clouds / Flavors': FlavorAllView,
    'Compute / Clouds / Availability Zones': AvailabilityZoneAllView,
    'Compute / Clouds / Stacks': StackAllView,
}


@pytest.fixture(scope='module', params=['5', '10', '20', '50', '100', '200', '500', '1000'])
def value(request):
    return request.param


@pytest.fixture(scope='module', params=[CloudProvider,
                                        'cloud_av_zones',
                                        'cloud_tenants',
                                        'cloud_flavors',
                                        'cloud_instances',
                                        'cloud_stacks',
                                        'cloud_keypairs'])
def page(request):
    return request.param


@pytest.fixture(scope='module')
def set_grid(appliance):
    old_grid_limit = appliance.user.my_settings.visual.grid_view_limit
    appliance.user.my_settings.visual.grid_view_limit = 5
    yield
    appliance.user.my_settings.visual.grid_view_limit = old_grid_limit


@pytest.fixture(scope='module')
def set_tile(appliance):
    tilelimit = appliance.user.my_settings.visual.tile_view_limit
    appliance.user.my_settings.visual.tile_view_limit = 5
    yield
    appliance.user.my_settings.visual.tile_view_limit = tilelimit


@pytest.fixture(scope='module')
def set_list(appliance):
    listlimit = appliance.user.my_settings.visual.list_view_limit
    appliance.user.my_settings.visual.list_view_limit = 5
    yield
    appliance.user.my_settings.visual.list_view_limit = listlimit


def set_default_page(appliance):
    appliance.user.my_settings.visual.set_login_page = 'Cloud Intelligence / Dashboard'


def go_to_grid(page):
    view = navigate_to(page, 'All')
    view.toolbar.view_selector.select('Grid View')


@pytest.fixture(scope='module')
def set_cloud_provider_quad(appliance):
    appliance.user.my_settings.visual.cloud_provider_quad = False
    yield
    appliance.user.my_settings.visual.cloud_provider_quad = True


def test_cloud_grid_page_per_item(appliance, request, page, value, set_grid):
    """ Tests grid items per page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    if isinstance(page, six.string_types):
        page = getattr(appliance.collections, page)
    if appliance.user.my_settings.visual.grid_view_limit != value:
        appliance.user.my_settings.visual.grid_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = appliance.user.my_settings.visual.grid_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select('Grid View')
    max_item = view.entities.paginator.max_item
    item_amt = view.entities.paginator.items_amount
    items_per_page = view.entities.paginator.items_per_page

    assert int(items_per_page) == int(limit)

    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), 'Gridview Failed for page {}!'.format(page)
    assert int(max_item) <= int(item_amt)


def test_cloud_tile_page_per_item(appliance, request, page, value, set_tile):
    """ Tests tile items per page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    if isinstance(page, six.string_types):
        page = getattr(appliance.collections, page)
    if appliance.user.my_settings.visual.tile_view_limit != value:
        appliance.user.my_settings.visual.tile_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = appliance.user.my_settings.visual.tile_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select('Tile View')
    max_item = view.entities.paginator.max_item
    item_amt = view.entities.paginator.items_amount
    items_per_page = view.entities.paginator.items_per_page

    assert int(items_per_page) == int(limit)

    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), 'Tileview Failed for page {}!'.format(page)
    assert int(max_item) <= int(item_amt)


def test_cloud_list_page_per_item(appliance, request, page, value, set_list):
    """ Tests list items per page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    if isinstance(page, six.string_types):
        page = getattr(appliance.collections, page)
    if appliance.user.my_settings.visual.list_view_limit != value:
        appliance.user.my_settings.visual.list_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = appliance.user.my_settings.visual.list_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select('List View')
    max_item = view.entities.paginator.max_item
    item_amt = view.entities.paginator.items_amount
    items_per_page = view.entities.paginator.items_per_page

    assert int(items_per_page) == int(limit)

    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), 'Listview Failed for page {}!'.format(page)
    assert int(max_item) <= int(item_amt)


@pytest.mark.parametrize('start_page', landing_pages, scope='module')
def test_cloud_start_page(request, appliance, start_page):
    """ Tests start page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/6h
        tags: settings
    """
    request.addfinalizer(lambda: set_default_page(appliance))
    appliance.user.my_settings.visual.login_page = start_page
    appliance.server.logout()
    appliance.server.login_admin()
    appliance.browser.create_view(landing_pages[start_page], wait='10s')


def test_cloudprovider_noquads(request, set_cloud_provider_quad):
    """
    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    view = navigate_to(CloudProvider, 'All')
    view.toolbar.view_selector.select('Grid View')
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data
