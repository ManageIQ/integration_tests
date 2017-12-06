# -*- coding: utf-8 -*-

from copy import copy
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


@pytest.fixture(scope='module', params=[InfraProvider, vms.Vm])
def page(request):
    return request.param


@pytest.fixture(scope='module', params=['10', '20', '50', '100', '200', '500', '1000'])
def value(request):
    return request.param


LANDING_PAGES = [
    # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1331327
    # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1331399
    # TODO: update landing_pages once these bugs are fixed.
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
    max_item = view.entities.paginator.max_item
    item_amt = view.entities.paginator.items_amount
    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), "Gridview Failed for page {}!".format(page)
    assert int(max_item) <= int(item_amt)


@pytest.mark.meta(blockers=[1267148])
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
    max_item = view.entities.paginator.max_item
    item_amt = view.entities.paginator.items_amount
    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), "Tileview Failed for page {}!".format(page)
    assert int(max_item) <= int(item_amt)


@pytest.mark.meta(blockers=[1267148])
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
    max_item = view.entities.paginator.max_item
    item_amt = view.entities.paginator.items_amount
    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), "Listview Failed for page {}!".format(page)
    assert int(max_item) <= int(item_amt)


@pytest.mark.meta(blockers=[1267148, 1273529])
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
    max_item = view.paginator.max_item
    item_amt = view.paginator.items_amount
    if int(item_amt) >= int(limit):
        assert int(max_item) == int(limit), "Reportview Failed!"
    assert int(max_item) <= int(item_amt)


@pytest.mark.uncollect('Needs to be fixed after menu removed')
@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize('start_page', LANDING_PAGES, scope="module")
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
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data


def test_host_noquads(appliance, request, set_host_quad):
    """
        This test checks that Host Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Host Quadrants" option works properly.
    """
    host_collection = appliance.collections.hosts
    view = navigate_to(host_collection, 'All')
    view.toolbar.view_selector.select("Grid View")
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data


def test_datastore_noquads(request, set_datastore_quad, appliance):
    """
        This test checks that Host Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Datastores Quadrants" option works properly.
    """
    dc = DatastoreCollection(appliance)
    view = navigate_to(dc, 'All')
    view.toolbar.view_selector.select("Grid View")
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data


def test_vm_noquads(request, set_vm_quad):
    """
        This test checks that VM Quadrant when switched off from Mysetting page under
        Visual Tab under "Show VM Quadrants" option works properly.
    """
    view = navigate_to(vms.Vm, 'VMsOnly')
    view.toolbar.view_selector.select("Grid View")
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:11215'])
def test_template_noquads(request, set_template_quad):
    """
        This test checks that Template Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Template Quadrants" option works properly.
    """
    view = navigate_to(vms.Template, 'TemplatesOnly')
    view.toolbar.view_selector.select("Grid View")
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data
