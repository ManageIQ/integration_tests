# -*- coding: utf-8 -*-

from copy import copy
import pytest

from cfme import login
from cfme import test_requirements
from cfme.configure.settings import visual
from cfme.intelligence.reports.reports import CannedSavedReport
from cfme.web_ui import paginator, toolbar as tb
from utils.providers import setup_a_provider as _setup_a_provider
from cfme.infrastructure import virtual_machines as vms  # NOQA
from cfme.infrastructure.provider import InfraProvider
from utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.host import Host
from cfme.infrastructure.datastore import Datastore

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]

# todo: infrastructure hosts, pools, stores, cluster are removed due to changing
# navigation to navmazing. all items have to be put back once navigation change is fully done

grid_pages = [
    InfraProvider,
    vms.Vm,
]

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


@pytest.fixture(scope="module")
def setup_a_provider():
    return _setup_a_provider(prov_class="infra", validate=True, check_existing=True)


@pytest.yield_fixture(scope="module")
def set_grid():
    gridlimit = visual.grid_view_limit
    visual.grid_view_limit = 5
    yield
    visual.grid_view_limit = gridlimit


@pytest.yield_fixture(scope="module")
def set_tile():
    tilelimit = visual.tile_view_limit
    visual.tile_view_limit = 5
    yield
    visual.tile_view_limit = tilelimit


@pytest.yield_fixture(scope="module")
def set_list():
    listlimit = visual.list_view_limit
    visual.list_view_limit = 5
    yield
    visual.list_view_limit = listlimit


@pytest.yield_fixture(scope="module")
def set_report():
    reportlimit = visual.report_view_limit
    visual.report_view_limit = 5
    yield
    visual.report_view_limit = reportlimit


def set_default_page():
    visual.set_login_page = "Cloud Intelligence / Dashboard"


def go_to_grid(page):
    navigate_to(page, 'All')
    tb.select('Grid View')


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
@pytest.mark.parametrize('page', grid_pages, scope="module")
def test_grid_page_per_item(request, setup_a_provider, page, set_grid):
    """ Tests grid items per page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.grid_view_limit
    navigate_to(page, 'All')
    tb.select('Grid View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Gridview Failed for page {}!".format(page)


@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize('page', grid_pages, scope="module")
def test_tile_page_per_item(request, setup_a_provider, page, set_tile):
    """ Tests tile items per page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.tile_view_limit
    navigate_to(page, 'All')
    tb.select('Tile View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Tileview Failed for page {}!".format(page)


@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize('page', grid_pages, scope="module")
def test_list_page_per_item(request, setup_a_provider, page, set_list):
    """ Tests list items per page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(lambda: go_to_grid(page))
    limit = visual.list_view_limit
    navigate_to(page, 'All')
    tb.select('List View')
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Listview Failed for page {}!".format(page)


@pytest.mark.meta(blockers=[1267148, 1273529])
def test_report_page_per_item(setup_a_provider, set_report):
    """ Tests report items per page

    Metadata:
        test_flag: visuals
    """
    path = ["Configuration Management", "Virtual Machines", "VMs Snapshot Summary"]
    limit = visual.report_view_limit
    report = CannedSavedReport.new(path)
    report.navigate()
    if int(paginator.rec_total()) >= int(limit):
        assert int(paginator.rec_end()) == int(limit), "Reportview Failed!"


@pytest.mark.uncollect('Needs to be fixed after menu removed')
@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize('start_page', landing_pages, scope="module")
def test_start_page(request, setup_a_provider, start_page):
    """ Tests start page

    Metadata:
        test_flag: visuals
    """
    request.addfinalizer(set_default_page)
    if visual.login_page != start_page:
        visual.login_page = start_page
    login.logout()
    login.login_admin()
    steps = map(lambda x: x.strip(), start_page.split('/'))
    longer_steps = copy(steps)
    longer_steps.insert(0, None)
    # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1331327
    # nav = menu.nav
    # nav.initialize()
    # assert nav.is_page_active(*steps) or nav.is_page_active(*longer_steps), "Landing Page Failed"


def test_infraprovider_noquads(request, setup_a_provider, set_infra_provider_quad):
    navigate_to(setup_a_provider, 'All')
    assert visual.check_image_exists, "Image View Failed!"


def test_host_noquads(request, setup_a_provider, set_host_quad):
    navigate_to(Host, 'All')
    assert visual.check_image_exists, "Image View Failed!"


def test_datastore_noquads(request, setup_a_provider, set_datastore_quad):
    navigate_to(Datastore, 'All')
    assert visual.check_image_exists, "Image View Failed!"


def test_vm_noquads(request, setup_a_provider, set_vm_quad):
    navigate_to(vms.Vm, 'All')
    assert visual.check_image_exists, "Image View Failed!"


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:11215'])
def test_template_noquads(request, setup_a_provider, set_template_quad):
    navigate_to(vms.Template, 'TemplatesOnly')
    assert visual.check_image_exists, "Image View Failed!"
