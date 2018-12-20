# -*- coding: utf-8 -*-
import pytest
import six

from copy import copy

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


def set_default_page(appliance):
    appliance.user.my_settings.visual.set_login_page = 'Cloud Intelligence / Dashboard'


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
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
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


def test_infra_tile_page_per_item(appliance, request, page, value, set_tile):
    """ Tests tile items per page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/10h
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


def test_infra_list_page_per_item(appliance, request, page, value, set_list):
    """ Tests list items per page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/10h
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


@pytest.mark.ignore_stream("5.9")
def test_infra_report_page_per_item(appliance, value, set_report, get_report):
    """ Tests report items per page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/10h
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


@pytest.mark.uncollect('Needs to be fixed after menu removed')
@pytest.mark.meta(blockers=[1267148])
@pytest.mark.parametrize('start_page', LANDING_PAGES, scope="module")
def test_infra_start_page(visual, request, appliance, start_page):
    """ Tests start page

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/6h
    """
    request.addfinalizer(set_default_page)
    if appliance.user.my_settings.visual.login_page != start_page:
        appliance.user.my_settings.visual.login_page = start_page
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

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/10h
    """
    view = navigate_to(InfraProvider, 'All')
    view.toolbar.view_selector.select('Grid View')
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data


def test_host_noquads(appliance, request, set_host_quad):
    """
        This test checks that Host Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Host Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/10h
    """
    host_collection = appliance.collections.hosts
    view = navigate_to(host_collection, 'All')
    view.toolbar.view_selector.select('Grid View')
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data


def test_datastore_noquads(request, set_datastore_quad, appliance):
    """
        This test checks that Host Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Datastores Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/10h
    """
    dc = DatastoreCollection(appliance)
    view = navigate_to(dc, 'All')
    view.toolbar.view_selector.select('Grid View')
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data


def test_vm_noquads(appliance, request, set_vm_quad):
    """
        This test checks that VM Quadrant when switched off from Mysetting page under
        Visual Tab under "Show VM Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/10h
    """
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    view.toolbar.view_selector.select('Grid View')
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:11215'])
def test_template_noquads(appliance, set_template_quad):
    """
        This test checks that Template Quadrant when switched off from Mysetting page under
        Visual Tab under "Show Template Quadrants" option works properly.

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/10h
    """
    view = navigate_to(appliance.collections.infra_templates, 'TemplatesOnly')
    view.toolbar.view_selector.select('Grid View')
    # Here data property will return an empty dict when the Quadrants option is deactivated.
    assert not view.entities.get_first_entity().data
