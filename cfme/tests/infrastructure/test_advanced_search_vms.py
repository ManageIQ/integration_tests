#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the view.search box in the VMs section"""
import fauxfactory
import pytest
from random import sample

from cfme.infrastructure import virtual_machines
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm
from fixtures.provider import setup_one_or_skip
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.web_ui.cfme_exception import (assert_no_cfme_exception,
    is_cfme_exception, cfme_exception_text)
from cfme.utils.providers import ProviderFilter

pytestmark = [pytest.mark.tier(3)]

@pytest.fixture(scope="module")
def a_provider(request):
    pf = ProviderFilter(classes=[InfraProvider], required_fields=['large'])
    setup_one_or_skip(request, filters=[pf])


@pytest.fixture(scope="module")
def vms(a_provider):
    """Ensure the infra providers are set up and get list of vms"""
    view = navigate_to(Vm, 'VMsOnly')
    view.search.remove_search_filters()
    return virtual_machines.get_all_vms()

@pytest.fixture(scope="module")
def subset_of_vms(vms):
    """We'll pick a host with median number of vms"""
    vm_num = 4 if len(vms) >= 4 else len(vms)
    return sample(vms, vm_num)


@pytest.fixture(scope="module")
def expression_for_vms_subset(subset_of_vms):
    return ";select_first_expression;click_or;".join(
        ["fill_field(Virtual Machine : Name, =, {})".format(vm) for vm in subset_of_vms]
    )


def test_can_do_advanced_search():
    view = navigate_to(Vm, 'VMsOnly')
    assert view.search.is_advanced_search_possible, "Cannot do advanced view.search here!"


@pytest.mark.requires("test_can_do_advanced_search")
def test_can_open_advanced_search(request):
    view = navigate_to(Vm, 'VMsOnly')
    view.search.open_advanced_search()
    request.addfinalizer(lambda: view.search.close_advanced_search())


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_without_user_input(request, vms, subset_of_vms, expression_for_vms_subset):
    view = navigate_to(Vm, 'VMsOnly')
    request.addfinalizer(lambda: view.search.close_advanced_search())
    # Set up the filter
    view.search.advanced_search(expression_for_vms_subset)
    view.flash.assert_no_error()
    vms_present = virtual_machines.get_all_vms(do_not_navigate=True)
    for vm in subset_of_vms:
        if vm not in vms_present:
            pytest.fail("Could not find VM {} after filtering!".format(vm))


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input(request, vms, subset_of_vms, expression_for_vms_subset):
    view = navigate_to(Vm, 'VMsOnly')
    request.addfinalizer(lambda: view.search.close_advanced_search())
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    view.search.advanced_search(
        "fill_field(Virtual Machine : Name, =)", {"Virtual Machine": vm}
    )
    view.flash.assert_no_error()
    vms_present = virtual_machines.get_all_vms(do_not_navigate=True)
    if vm not in vms_present:
        pytest.fail("Could not find VM {} after filtering!".format(vm))


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input_and_cancellation(request, vms, subset_of_vms,
                                                 expression_for_vms_subset):
    view = navigate_to(Vm, 'VMsOnly')
    request.addfinalizer(lambda: view.search.close_advanced_search())
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    view.search.advanced_search(
        "fill_field(Virtual Machine : Name, =)",
        {"Virtual Machine": vm},
        cancel_on_user_filling=True
    )
    view.flash.assert_no_error()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_cancel(request, vms, subset_of_vms, expression_for_vms_subset):
    view = navigate_to(Vm, 'VMsOnly')
    request.addfinalizer(lambda: view.search.close_advanced_search())
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up the filter
    view.search.save_filter(
        "fill_field(Virtual Machine : Name, =)",
        filter_name,
        cancel=True
    )
    view.flash.assert_no_error()
    with pytest.raises(view.search.DisabledButtonException):
        view.search.load_filter(filter_name)  # does not exist


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_load(request, vms, subset_of_vms, expression_for_vms_subset):
    view = navigate_to(Vm, 'VMsOnly')
    request.addfinalizer(lambda: view.search.close_advanced_search())
    filter_name = fauxfactory.gen_alphanumeric()
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    view.search.save_filter("fill_field(Virtual Machine : Name, =)", filter_name)
    view.flash.assert_no_error()
    view.search.reset_filter()

    view.search.load_filter(filter_name, fill_callback={"Virtual Machine": vm}, apply_filter=True)
    view.flash.assert_no_error()
    request.addfinalizer(view.search.delete_filter)
    assert vm in virtual_machines.get_all_vms(do_not_navigate=True)


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_cancel_load(request):
    view = navigate_to(Vm, 'VMsOnly')
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up the filter
    view.search.save_filter("fill_field(Virtual Machine : Name, =)", filter_name)

    @request.addfinalizer
    def cleanup():
        navigate_to(Vm, 'VMsOnly')
        view.search.load_filter(filter_name)
        view.search.delete_filter()
        view.search.close_advanced_search()

    view.flash.assert_no_error()
    view.search.reset_filter()

    view.search.load_filter(filter_name, cancel=True)
    view.flash.assert_no_error()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_load_cancel(request, vms, subset_of_vms):
    view = navigate_to(Vm, 'VMsOnly')
    filter_name = fauxfactory.gen_alphanumeric()
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    view.search.save_filter("fill_field(Virtual Machine : Name, =)", filter_name)

    @request.addfinalizer
    def cleanup():
        navigate_to(Vm, 'VMsOnly')
        view.search.load_filter(filter_name)
        view.search.delete_filter()
        view.search.close_advanced_search()

    view.flash.assert_no_error()
    view.search.reset_filter()

    view.search.load_filter(
        filter_name,
        fill_callback={"Virtual Machine": vm},
        cancel_on_user_filling=True,
        apply_filter=True
    )
    view.flash.assert_no_error()


def test_quick_search_without_filter(request, vms, subset_of_vms):
    view = navigate_to(Vm, 'VMsOnly')
    view.search.remove_search_filters()
    view.flash.assert_no_error()
    vm = sample(subset_of_vms, 1)[0]
    # Make sure that we empty the regular view.search field after the test
    request.addfinalizer(view.search.clear_simple_search())
    # Filter this host only
    view.search.simple_search(vm)
    view.flash.assert_no_error()
    # Check it is there
    all_vms_visible = virtual_machines.get_all_vms(do_not_navigate=True)
    assert len(all_vms_visible) == 1 and vm in all_vms_visible


@pytest.mark.requires("test_can_open_advanced_search")
def test_quick_search_with_filter(request, vms, subset_of_vms, expression_for_vms_subset):
    view = navigate_to(Vm, 'VMsOnly')
    request.addfinalizer(view.search.close_advanced_search)
    view.search.advanced_search(expression_for_vms_subset)
    view.flash.assert_no_error()
    # Make sure that we empty the regular view.search field after the test
    request.addfinalizer(view.search.clear_simple_search)
    # Filter this host only
    chosen_vm = sample(subset_of_vms, 1)[0]
    view.search.simple_search(chosen_vm)
    view.flash.assert_no_error()
    # Check it is there
    all_vms_visible = virtual_machines.get_all_vms(do_not_navigate=True)
    assert len(all_vms_visible) == 1 and chosen_vm in all_vms_visible


def test_can_delete_filter(request):
    view = navigate_to(Vm, 'VMsOnly')
    request.addfinalizer(view.search.close_advanced_search)
    filter_name = fauxfactory.gen_alphanumeric()
    view.search.save_filter("fill_count(Virtual Machine.Files, >, 0)", filter_name)
    view.flash.assert_no_error()
    view.search.reset_filter()
    view.flash.assert_no_error()
    view.search.load_filter(filter_name)
    view.flash.assert_no_error()
    if not view.search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    view.flash.assert_no_error()


def test_delete_button_should_appear_after_save(request):
    """Delete button appears only after load, not after save"""
    view = navigate_to(Vm, 'VMsOnly')
    filter_name = fauxfactory.gen_alphanumeric()
    view.search.save_filter("fill_count(Virtual Machine.Files, >, 0)", filter_name)

    @request.addfinalizer
    def cleanup():
        view = navigate_to(Vm, 'VMsOnly')
        view.search.load_filter(filter_name)
        view.search.delete_filter()
        view.search.close_advanced_search()

    if not view.search.delete_filter():  # Returns False if the button is not present
        pytest.fail("Could not delete filter right after saving!")


def test_cannot_delete_more_than_once(request, nuke_browser_after_test):
    """When Delete button appars, it does not want to go away"""
    view = navigate_to(Vm, 'VMsOnly')
    request.addfinalizer(view.search.close_advanced_search)
    filter_name = fauxfactory.gen_alphanumeric()
    view.search.save_filter("fill_count(Virtual Machine.Files, >, 0)", filter_name)

    view.search.load_filter(filter_name)  # circumvent the thing happening in previous test
    # Delete once
    if not view.search.delete_filter():
        pytest.fail("Could not delete the filter even first time!")
    view.flash.assert_no_error()
    # Try it second time
    if view.search.delete_filter():  # If the button is there, it says True
        # This should not happen
        msg = "Delete twice accepted!"
        if is_cfme_exception():
            msg += " CFME Exception text: `{}`".format(cfme_exception_text())
        pytest.fail(msg)
