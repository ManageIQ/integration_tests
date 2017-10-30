# -*- coding: utf-8 -*-

from copy import copy
import itertools
import pytest
from cfme import test_requirements
from cfme.configure.settings import visual
from cfme.intelligence.reports.reports import CannedSavedReport
from cfme.infrastructure import virtual_machines as vms  # NOQA
from cfme.infrastructure.datastore import DatastoreCollection
from cfme.infrastructure.provider import InfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures("infra_provider")]

# todo: infrastructure hosts, pools, stores, cluster are removed due to changing
# navigation to navmazing. all items have to be put back once navigation change is fully done


def get_parameter(view):
    grid_pages = [
        InfraProvider,
        vms.Vm,
    ]
    if "grid" in view:
        value = visual.grid_view_entities
    elif "tile" in view:
        value = visual.tile_view_entities
    else:
        value = visual.list_view_entities
    parameter = itertools.product(value, grid_pages)
    return parameter


report_parameter = ['5', '10', '20', '50', '100', '200', '500', '1000']

# BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1331327
# BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1331399
# TODO: update landing_pages once these bugs are fixed.
landing_pages = [
    'Cloud Intel / Dashboard',
    'Services / My Services',
    'Services / Catalogs',
    'Services / Requests',
    'Infrastructure / Providers',
    'Infrastructure / Clusters',
    'Infrastructure / Hosts',
    'Infrastructure / Resource Pools',
    'Infrastructure / Datastores',
    'Control / Explorer',
    'Automate / Explorer',
    'Optimize / Utilization',
    'Optimize / Planning',
    'Optimize / Bottlenecks',
]


@pytest.yield_fixture(scope="module")
def set_grid():
    gridlimit = visual.grid_view_limit
    yield
    visual.grid_view_limit = gridlimit


@pytest.yield_fixture(scope="module")
def set_tile():
    tilelimit = visual.tile_view_limit
    yield
    visual.tile_view_limit = tilelimit


@pytest.yield_fixture(scope="module")
def set_list():
    listlimit = visual.list_view_limit
    yield
    visual.list_view_limit = listlimit


@pytest.yield_fixture(scope="module")
def set_report():
    reportlimit = visual.report_view_limit
    yield
    visual.report_view_limit = reportlimit


def set_default_page():
    visual.set_login_page = "Cloud Intelligence / Dashboard"


def go_to_grid(page):
    view = navigate_to(page, 'All')
    view.toolbar.view_selector.select('Grid View')


@pytest.yield_fixture(scope="module")
def set_infra_provider_quad():
    visual.infra_provider_quad = False
    yield
    visual.infra_provider_quad = True


@pytest.yield_fixture(scope="module")
def set_host_quad():
    visual.host_quad = False
    yield
    visual.host_quad = True


@pytest.yield_fixture(scope="module")
def set_datastore_quad():
    visual.datastore_quad = False
    yield
    visual.datastore_quad = True


@pytest.yield_fixture(scope="module")
def set_vm_quad():
    visual.vm_quad = False
    yield
    visual.vm_quad = True


@pytest.yield_fixture(scope="module")
def set_template_quad():
    visual.template_quad = False
    yield
    visual.template_quad = True


@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize("value, page", get_parameter("grid"), scope="module")
def test_infra_grid_page_per_item(request, page, value, set_grid):
    """ Tests grid items per page

    Metadata:
        test_flag: visuals
    """
    if visual.grid_view_limit != value:
        visual.grid_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.grid_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select("Grid View")
    min_item, max_item, item_amt = view.paginator.paginator.page_info()
    if int(view.paginator.items_amount) >= int(limit):
        assert int(max_item) == int(limit), "Gridview Failed for page {}!".format(page)
    assert int(max_item) <= int(item_amt)


@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize("value, page", get_parameter("tile"), scope="module")
def test_infra_tile_page_per_item(request, page, value, set_tile):
    """ Tests tile items per page

    Metadata:
        test_flag: visuals
    """
    if visual.tile_view_limit != value:
        visual.tile_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.tile_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select('Tile View')
    min_item, max_item, item_amt = view.paginator.paginator.page_info()
    if int(view.paginator.items_amount) >= int(limit):
        assert int(max_item) == int(limit), "Tileview Failed for page {}!".format(page)
    assert int(max_item) <= int(item_amt)


@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize("value, page", get_parameter("list"), scope="module")
def test_infra_list_page_per_item(request, page, value, set_list):
    """ Tests list items per page

    Metadata:
        test_flag: visuals
    """
    if visual.list_view_limit != value:
        visual.list_view_limit = int(value)
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.list_view_limit
    view = navigate_to(page, 'All', use_resetter=False)
    view.toolbar.view_selector.select('List View')
    min_item, max_item, item_amt = view.paginator.paginator.page_info()
    if int(view.paginator.items_amount) >= int(limit):
        assert int(max_item) == int(limit), "Listview Failed for page {}!".format(page)
    assert int(max_item) <= int(item_amt)


@pytest.mark.meta(blockers=[1267148, 1273529])
@pytest.mark.parametrize("value", report_parameter, scope="module")
def test_infra_report_page_per_item(value, set_report):
    """ Tests report items per page

    Metadata:
        test_flag: visuals
    """
    visual.report_view_limit = value
    path = ["Configuration Management", "Virtual Machines", "VMs Snapshot Summary"]
    limit = visual.report_view_limit
    report = CannedSavedReport.new(path)
    view = navigate_to(report, 'Details')
    min_item, max_item, item_amt = view.paginator.paginator.page_info()
    if int(view.paginator.items_amount) >= int(limit):
        assert int(max_item) == int(limit), "Reportview Failed!"
    assert int(max_item) <= int(item_amt)


@pytest.mark.uncollect('Needs to be fixed after menu removed')
@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize('start_page', landing_pages, scope="module")
def test_infra_start_page(request, appliance, start_page):
    """ Tests start page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(set_default_page)
    if visual.login_page != start_page:
        visual.login_page = start_page
    appliance.server.logout()
    appliance.server.login_admin()
    steps = map(lambda x: x.strip(), start_page.split('/'))
    longer_steps = copy(steps)
    longer_steps.insert(0, None)
    # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1331327
    # nav = menu.nav
    # nav.initialize()
    # assert nav.is_page_active(*steps) or nav.is_page_active(*longer_steps), "Landing Page Failed"


def test_infraprovider_noquads(request, set_infra_provider_quad):
    """
        This test checks that Infraprovider Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Infrastructure Provider Quadrants" option works properly.
    """
    view = navigate_to(InfraProvider, 'All')
    view.toolbar.view_selector.select("Grid View")
    # Here get_first_entity() method will return None when the Quadrants option is deactivated.
    assert view.entities.get_first_entity().data is None


def test_host_noquads(appliance, request, set_host_quad):
    """
        This test checks that Host Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Host Quadrants" option works properly.
    """
    host_collection = appliance.collections.hosts
    view = navigate_to(host_collection, 'All')
    view.toolbar.view_selector.select("Grid View")
    # Here get_first_entity() method will return None when the Quadrants option is deactivated.
    assert view.entities.get_first_entity().data is None


def test_datastore_noquads(request, set_datastore_quad, appliance):
    """
        This test checks that Host Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Datastores Quadrants" option works properly.
    """
    dc = DatastoreCollection(appliance)
    view = navigate_to(dc, 'All')
    view.toolbar.view_selector.select("Grid View")
    # Here get_first_entity() method will return None when the Quadrants option is deactivated.
    assert view.entities.get_first_entity().data is None
    # assert visual.check_image_exists, "Image View Failed!"


def test_vm_noquads(request, set_vm_quad):
    """
        This test checks that VM Quadrant when switched off from Mysetting page under
        Visual Tab under "Show VM Quadrants" option works properly.
    """
    view = navigate_to(vms.Vm, 'All')
    view.toolbar.view_selector.select("Grid View")
    # Here get_first_entity() method will return None when the Quadrants option is deactivated.
    assert view.entities.get_first_entity().data is None


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:11215'])
def test_template_noquads(request, set_template_quad):
    """
        This test checks that Template Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Template Quadrants" option works properly.
    """
    view = navigate_to(vms.Template, 'TemplatesOnly')
    view.toolbar.view_selector.select("Grid View")
    # Here get_first_entity() method will return None when the Quadrants option is deactivated.
    assert view.entities.get_first_entity().data is None
