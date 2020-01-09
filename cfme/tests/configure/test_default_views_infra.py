import random

import pytest

from cfme import test_requirements
from cfme.exceptions import ItemNotFound
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.workloads import TemplatesImages
from cfme.services.workloads import VmsInstances
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('virtualcenter_provider')]


# TODO refactor for setup_provider parametrization with new 'latest' tag
# TODO: infrastructure hosts, pools, stores, clusters, catalog items are removed
# due to navmazing or collections. all items have to be put back once navigation change is fully
# done

GTL_PARAMS = {
    'Infrastructure Providers': 'infra_providers',  # collection name
    'VMs': 'infra_vms',  # collection name
    'My Services': MyService,
    'VMs & Instances': VmsInstances,
    'Templates & Images': TemplatesImages,
    'Service Catalogs': ServiceCatalogs
}


def check_vm_visibility(appliance, check=False):
    view = navigate_to(appliance.collections.infra_vms, 'All')
    value = view.sidebar.vmstemplates.tree.read_contents()
    # Below steps assigns last name of the last list to vm_name variable.
    vm_name = value[-1]
    while isinstance(vm_name, list):
        vm_name = vm_name[-1]
    if vm_name == "<Orphaned>" and not check:
        return False
    if vm_name == "<Orphaned>" and check:
        view.sidebar.vmstemplates.tree.click_path("All VMs & Templates", vm_name)
        try:
            view.entities.get_first_entity()
        except ItemNotFound:
            pass
    return True


# BZ 1283118 written against 5.5 has a mix of what default views do and don't work on different
# pages in different releases

def _get_page(page, appliance):
    """This is a bit of a hack, but I currently don't see a way around it"""
    if page in [TemplatesImages, VmsInstances]:
        # one-off instantiation of class
        return page(appliance)
    if isinstance(page, str):
        # Appliance collection instantiation of class
        return getattr(appliance.collections, page)
    # Nav class provided
    return page


def test_default_view_infra_reset(appliance):
    """This test case performs Reset button test.

    Steps:
        * Navigate to DefaultViews page
        * Check Reset Button is disabled
        * Select 'infrastructure_providers' button from infrastructure region
        * Change it's default mode
        * Check Reset Button is enabled

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: high
        initialEstimate: 1/20h
        tags: settings
    """
    view = navigate_to(appliance.user.my_settings, "DefaultViews")
    assert view.tabs.default_views.reset.disabled
    infra_btn = view.tabs.default_views.infrastructure.infrastructure_providers
    views = ['Tile View', 'Grid View', 'List View']
    views.remove(infra_btn.active_button)
    infra_btn.select_button(random.choice(views))
    assert not view.tabs.default_views.reset.disabled


@pytest.mark.parametrize('group_name', list(GTL_PARAMS.keys()), scope="module")
@pytest.mark.parametrize('view', ['List View', 'Tile View', 'Grid View'])
@pytest.mark.uncollectif(lambda view, group_name:
                         view == "Grid View" and group_name == "Service Catalogs",
                         reason='Invalid combination of grid view and service catalogs')
def test_infra_default_view(appliance, group_name, view):
    """This test case changes the default view of an infra related page and asserts the change.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: high
        initialEstimate: 1/10h
        tags: settings

    Bugzilla:
        1553337
    """
    page = _get_page(GTL_PARAMS[group_name], appliance)
    default_views = appliance.user.my_settings.default_views
    old_default = default_views.get_default_view(group_name)
    default_views.set_default_view(group_name, view)
    dest = 'All'
    if group_name == 'VMs':
        dest = 'VMsOnly'
    selected_view = navigate_to(page, dest, use_resetter=False).toolbar.view_selector.selected
    assert view == selected_view, '{} view setting failed'.format(view)
    default_views.set_default_view(group_name, old_default)


@pytest.mark.parametrize('expected_view',
                         ['Expanded View', 'Compressed View', 'Details Mode', 'Exists Mode'])
def test_infra_compare_view(appliance, expected_view):
    """This test changes the default view/mode for comparison between infra provider instances
    and asserts the change.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: high
        initialEstimate: 1/10h
        tags: settings
    """
    if expected_view in ['Expanded View', 'Compressed View']:
        group_name, selector_type = 'Compare', 'views_selector'
    else:
        group_name, selector_type = 'Compare Mode', 'modes_selector'
    default_views = appliance.user.my_settings.default_views
    old_default = default_views.get_default_view(group_name)
    default_views.set_default_view(group_name, expected_view)
    vm_view = navigate_to(appliance.collections.infra_vms, 'All')
    e_slice = slice(0, 2, None)
    [e.ensure_checked() for e in vm_view.entities.get_all(slice=e_slice)]
    vm_view.toolbar.configuration.item_select('Compare Selected items')
    selected_view = getattr(vm_view.actions, selector_type).selected
    assert expected_view == selected_view, '{} setting failed'.format(expected_view)
    default_views.set_default_view(group_name, old_default)


@pytest.mark.ignore_stream("5.11")
def test_vm_visibility_off(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/10h
        tags: settings
        endsin: 5.10
    """
    appliance.user.my_settings.default_views.set_default_view_switch_off()
    assert not check_vm_visibility(appliance)


@pytest.mark.ignore_stream("5.11")
def test_vm_visibility_on(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/5h
        tags: settings
        endsin: 5.10
    """
    appliance.user.my_settings.default_views.set_default_view_switch_on()
    assert check_vm_visibility(appliance, check=True)
