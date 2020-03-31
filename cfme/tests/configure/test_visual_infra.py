from random import choice

import pytest

from cfme import test_requirements
from cfme.infrastructure import virtual_machines as vms  # NOQA
from cfme.infrastructure.datastore import DatastoreCollection
from cfme.infrastructure.provider import InfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('infra_provider')]

# todo: infrastructure hosts, pools, stores, cluster are removed due to changing
# navigation to navmazing. all items have to be put back once navigation change is fully done


@pytest.fixture(scope='module', params=['datastores', 'hosts', 'infra_providers', 'infra_vms'])
def page(request):
    return request.param


@pytest.fixture(scope='module', params=['5', '10', '20', '50', '100', '200', '500', '1000'])
def value(request):
    return request.param


@pytest.fixture(scope="module")
def get_report(appliance):
    saved_report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Virtual Machines",
        menu_name="VMs Snapshot Summary",
    ).queue(wait_for_finish=True)
    yield saved_report
    saved_report.delete(cancel=False)


@pytest.fixture(scope='module')
def set_grid(appliance):
    gridlimit = appliance.user.my_settings.visual.grid_view_limit
    yield
    appliance.user.my_settings.visual.grid_view_limit = gridlimit


@pytest.fixture(scope='module')
def set_tile(appliance):
    tilelimit = appliance.user.my_settings.visual.tile_view_limit
    yield
    appliance.user.my_settings.visual.tile_view_limit = tilelimit


@pytest.fixture(scope='module')
def set_list(appliance):
    listlimit = appliance.user.my_settings.visual.list_view_limit
    yield
    appliance.user.my_settings.visual.list_view_limit = listlimit


@pytest.fixture(scope='module')
def set_report(appliance):
    reportlimit = appliance.user.my_settings.visual.report_view_limit
    yield
    appliance.user.my_settings.visual.report_view_limit = reportlimit


def go_to_grid(page):
    view = navigate_to(page, 'All')
    view.toolbar.view_selector.select('Grid View')


@pytest.fixture(scope='module')
def set_infra_provider_quad(appliance):
    appliance.user.my_settings.visual.infra_provider_quad = False
    yield
    appliance.user.my_settings.visual.infra_provider_quad = True


@pytest.fixture(scope='module')
def set_host_quad(appliance):
    appliance.user.my_settings.visual.host_quad = False
    yield
    appliance.user.my_settings.visual.host_quad = True


@pytest.fixture(scope='module')
def set_datastore_quad(appliance):
    appliance.user.my_settings.visual.datastore_quad = False
    yield
    appliance.user.my_settings.visual.datastore_quad = True


@pytest.fixture(scope='module')
def set_vm_quad(appliance):
    appliance.user.my_settings.visual.vm_quad = False
    yield
    appliance.user.my_settings.visual.vm_quad = True


@pytest.fixture(scope='module')
def set_template_quad(appliance):
    appliance.user.my_settings.visual.template_quad = False
    yield
    appliance.user.my_settings.visual.template_quad = True


def test_infra_grid_page_per_item(appliance, request, page, value, set_grid):
    """ Tests grid items per page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/12h
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
        assert int(max_item) == int(limit), f'Gridview Failed for page {page}!'
    assert int(max_item) <= int(item_amt)


def test_infra_tile_page_per_item(appliance, request, page, value, set_tile):
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
        assert int(max_item) == int(limit), f'Tileview Failed for page {page}!'
    assert int(max_item) <= int(item_amt)


def test_infra_list_page_per_item(appliance, request, page, value, set_list):
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
        assert int(max_item) == int(limit), f'Listview Failed for page {page}!'
    assert int(max_item) <= int(item_amt)


def test_infra_report_page_per_item(appliance, value, set_report, get_report):
    """ Tests report items per page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    appliance.user.my_settings.visual.report_view_limit = value
    limit = appliance.user.my_settings.visual.report_view_limit
    # Navigate to report's detail page.
    view = navigate_to(get_report.report, "Details")
    # Access the paginator on the `Saved Reports` tab of report's Details page.
    max_item = view.saved_reports.paginator.max_item
    item_amt = view.saved_reports.paginator.items_amount
    items_per_page = view.saved_reports.paginator.items_per_page

    assert int(items_per_page) == int(limit)
    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), "Reportview Failed!"

    assert int(max_item) <= int(item_amt)


def test_infraprovider_noquads(request, set_infra_provider_quad):
    """
        This test checks that Infraprovider Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Infrastructure Provider Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    view = navigate_to(InfraProvider, 'All')
    view.toolbar.view_selector.select('Grid View')
    assert 'topRight' not in view.entities.get_first_entity().data.get('quad', {})


def test_host_noquads(appliance, request, set_host_quad):
    """
        This test checks that Host Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Host Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    host_collection = appliance.collections.hosts
    view = navigate_to(host_collection, 'All')
    view.toolbar.view_selector.select('Grid View')
    assert 'topRight' not in view.entities.get_first_entity().data.get('quad', {})


def test_datastore_noquads(request, set_datastore_quad, appliance):
    """
        This test checks that Host Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Datastores Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    dc = DatastoreCollection(appliance)
    view = navigate_to(dc, 'All')
    view.toolbar.view_selector.select('Grid View')
    assert 'topRight' not in view.entities.get_first_entity().data.get('quad', {})


def test_vm_noquads(appliance, request, set_vm_quad):
    """
        This test checks that VM Quadrant when switched off from Mysetting page under
        Visual Tab under "Show VM Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    view.toolbar.view_selector.select('Grid View')
    assert 'topRight' not in view.entities.get_first_entity().data.get('quad', {})


def test_template_noquads(appliance, set_template_quad):
    """
        This test checks that Template Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Template Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
    """
    view = navigate_to(appliance.collections.infra_templates, 'TemplatesOnly')
    view.toolbar.view_selector.select('Grid View')
    assert 'topRight' not in view.entities.get_first_entity().data.get('quad', {})


def test_change_truncate_long_text_save_button_enabled(appliance):
    """
        This test checks if setting long_text enables the save button
        and if it is saved successfully

    Bugzilla:
        1650461

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
        setup:
            1. Navigate to Visual tab.
            2. Change the value of long_text.
        testSteps:
            1. See if save button is enabled.
            2. Save and check if the value was updated.
        expectedResults:
            1. Save button is enabled.
            2. Value is changed successfully.
    """
    view = navigate_to(appliance.user.my_settings, "Visual")
    visual = view.tabs.visual
    available_options = [option.text for option in visual.grid_tile_icons.long_text.all_options]
    available_options.remove(visual.grid_tile_icons.long_text.selected_option)
    selected_choice = choice(available_options)

    visual.grid_tile_icons.long_text.fill(selected_choice)
    assert not view.tabs.visual.save.disabled

    visual.save.click()
    assert visual.grid_tile_icons.long_text.selected_option == selected_choice
