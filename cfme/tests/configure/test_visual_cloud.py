import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('openstack_provider')]


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
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    if isinstance(page, str):
        page = getattr(appliance.collections, page)
    if appliance.user.my_settings.visual.grid_view_limit != value:
        appliance.user.my_settings.visual.grid_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = appliance.user.my_settings.visual.grid_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select('Grid View')
    if not view.entities.paginator.is_displayed:
        pytest.skip("This page doesn't have entities and/or paginator")
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
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    if isinstance(page, str):
        page = getattr(appliance.collections, page)
    if appliance.user.my_settings.visual.tile_view_limit != value:
        appliance.user.my_settings.visual.tile_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = appliance.user.my_settings.visual.tile_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select('Tile View')
    if not view.entities.paginator.is_displayed:
        pytest.skip("This page doesn't have entities and/or paginator")
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
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    if isinstance(page, str):
        page = getattr(appliance.collections, page)
    if appliance.user.my_settings.visual.list_view_limit != value:
        appliance.user.my_settings.visual.list_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = appliance.user.my_settings.visual.list_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select('List View')
    if not view.entities.paginator.is_displayed:
        pytest.skip("This page doesn't have entities and/or paginator")
    max_item = view.entities.paginator.max_item
    item_amt = view.entities.paginator.items_amount
    items_per_page = view.entities.paginator.items_per_page

    assert int(items_per_page) == int(limit)

    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), 'Listview Failed for page {}!'.format(page)
    assert int(max_item) <= int(item_amt)


def test_cloudprovider_noquads(request, set_cloud_provider_quad):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    view = navigate_to(CloudProvider, 'All')
    view.toolbar.view_selector.select('Grid View')
    assert 'topRight' not in view.entities.get_first_entity().data.get('quad', {})
