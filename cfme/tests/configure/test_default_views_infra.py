# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.configure.settings import DefaultView
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.myservice import MyService
from cfme.services.workloads import VmsInstances, TemplatesImages
from cfme.web_ui import toolbar as tb
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.exceptions import ItemNotFound

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('virtualcenter_provider')]


# TODO refactor for setup_provider parametrization with new 'latest' tag
# TODO: infrastructure hosts, pools, stores, clusters are removed
# due to navmazing. all items have to be put back once navigation change is fully done

gtl_params = {
    'Infrastructure Providers': InfraProvider,
    'VMs': Vm,
    'My Services': MyService,
    'Catalog Items': CatalogItem,
    'VMs & Instances': VmsInstances,
    'Templates & Images': TemplatesImages}


def set_and_test_default_view(group_name, view, page):
    old_default = DefaultView.get_default_view(group_name)
    DefaultView.set_default_view(group_name, view)
    dest = 'All'
    if group_name == 'VMs':
        dest = 'VMsOnly'
    navigate_to(page, dest, use_resetter=False)

    assert tb.is_active(view), "{} view setting failed".format(view)
    DefaultView.set_default_view(group_name, old_default)


def check_vm_visibility(check=False):
    view = navigate_to(Vm, 'All')
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


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_infra_tile_defaultview(key):
    set_and_test_default_view(key, 'Tile View', gtl_params[key])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_infra_list_defaultview(key):
    set_and_test_default_view(key, 'List View', gtl_params[key])


@pytest.mark.parametrize('key', gtl_params, scope="module")
def test_infra_grid_defaultview(key):
    set_and_test_default_view(key, 'Grid View', gtl_params[key])


def set_and_test_view(group_name, view):
    old_default = DefaultView.get_default_view(group_name)
    DefaultView.set_default_view(group_name, view)
    vm_view = navigate_to(Vm, 'All')
    [e.check() for e in vm_view.entities.get_all()[:2]]
    vm_view.toolbar.configuration.item_select('Compare Selected items')
    assert tb.is_active(view), "{} setting failed".format(view)
    DefaultView.set_default_view(group_name, old_default)


def test_infra_expanded_view():
    set_and_test_view('Compare', 'Expanded View')


def test_infra_compressed_view():
    set_and_test_view('Compare', 'Compressed View')


def test_infra_details_view():
    set_and_test_view('Compare Mode', 'Details Mode')


def test_infra_exists_view():
    set_and_test_view('Compare Mode', 'Exists Mode')


def test_vm_visibility_off():
    DefaultView.set_default_view_switch_off()
    assert not check_vm_visibility()


def test_vm_visibility_on():
    DefaultView.set_default_view_switch_on()
    assert check_vm_visibility(True)
