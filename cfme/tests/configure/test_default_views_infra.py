# -*- coding: utf-8 -*-
import pytest
from six import string_types

from cfme import test_requirements
from cfme.services.myservice import MyService
from cfme.services.workloads import VmsInstances, TemplatesImages
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.exceptions import ItemNotFound

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('virtualcenter_provider')]


# TODO refactor for setup_provider parametrization with new 'latest' tag
# TODO: infrastructure hosts, pools, stores, clusters, catalog items are removed
# due to navmazing or collections. all items have to be put back once navigation change is fully
# done

gtl_params = {
    'Infrastructure Providers': 'infra_providers',  # collection name
    'VMs': 'infra_vms',  # collection name
    'My Services': MyService,
    'VMs & Instances': VmsInstances,
    'Templates & Images': TemplatesImages
}


def set_and_test_default_view(appliance, group_name, view, page):
    default_views = appliance.user.my_settings.default_views
    old_default = default_views.get_default_view(group_name)
    default_views.set_default_view(group_name, view)
    dest = 'All'
    if group_name == 'VMs':
        dest = 'VMsOnly'
    selected_view = navigate_to(page, dest, use_resetter=False).toolbar.view_selector.selected
    assert view == selected_view, '{} view setting failed'.format(view)
    default_views.set_default_view(group_name, old_default)


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
    if isinstance(page, string_types):
        # Appliance collection instantiation of class
        return getattr(appliance.collections, page)
    # Nav class provided
    return page


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_infra_tile_defaultview(appliance, key):
    set_and_test_default_view(appliance, key, 'Tile View', _get_page(gtl_params[key], appliance))


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_infra_list_defaultview(appliance, key):
    set_and_test_default_view(appliance, key, 'List View', _get_page(gtl_params[key], appliance))


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_infra_grid_defaultview(appliance, key):
    set_and_test_default_view(appliance, key, 'Grid View', _get_page(gtl_params[key], appliance))


def set_and_test_compare_view(appliance, group_name, expected_view, selector_type='views_selector'):
    default_views = appliance.user.my_settings.default_views
    old_default = default_views.get_default_view(group_name)
    default_views.set_default_view(group_name, expected_view)
    vm_view = navigate_to(appliance.collections.infra_vms, 'All')
    [e.check() for e in vm_view.entities.get_all()[:2]]
    vm_view.toolbar.configuration.item_select('Compare Selected items')
    selected_view = getattr(vm_view.actions, selector_type).selected
    assert expected_view == selected_view, '{} setting failed'.format(expected_view)
    default_views.set_default_view(group_name, old_default)


def test_infra_expanded_view(appliance):
    set_and_test_compare_view(appliance, 'Compare', 'Expanded View')


def test_infra_compressed_view(appliance):
    set_and_test_compare_view(appliance, 'Compare', 'Compressed View')


def test_infra_details_mode(appliance):
    set_and_test_compare_view(appliance, 'Compare Mode', 'Details Mode', 'modes_selector')


def test_infra_exists_mode(appliance):
    set_and_test_compare_view(appliance, 'Compare Mode', 'Exists Mode', 'modes_selector')


def test_vm_visibility_off(appliance):
    appliance.user.my_settings.default_views.set_default_view_switch_off()
    assert not check_vm_visibility(appliance)


def test_vm_visibility_on(appliance):
    appliance.user.my_settings.default_views.set_default_view_switch_on()
    assert check_vm_visibility(appliance, check=True)
