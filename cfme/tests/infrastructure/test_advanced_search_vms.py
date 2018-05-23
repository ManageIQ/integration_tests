#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the view.entities.search box in the VMs section"""
from random import sample

import fauxfactory
import pytest
from widgetastic.exceptions import NoSuchElementException

from cfme.infrastructure import virtual_machines
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import InfraVm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.providers import ProviderFilter
from cfme.fixtures.provider import setup_one_or_skip

pytestmark = [pytest.mark.tier(3)]


@pytest.fixture(scope="module")
def a_provider(request):
    pf = ProviderFilter(classes=[InfraProvider], required_fields=['large'])
    setup_one_or_skip(request, filters=[pf])


@pytest.fixture(scope="module")
def vms(appliance, a_provider):
    """Ensure the infra providers are set up and get list of vms"""
    view = navigate_to(InfraVm, 'VMsOnly')
    view.entities.search.remove_search_filters()
    return virtual_machines.get_all_vms(appliance)


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


@pytest.fixture(scope="function")
def vm_advanced_search():
    view = navigate_to(InfraVm, 'VMsOnly')
    assert view.entities.search.is_advanced_search_possible, (
        "Cannot do advanced view.entities.search here!")
    yield view
    view.entities.search.remove_search_filters()


def test_can_open_vm_advanced_search(vm_advanced_search):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    vm_advanced_search.entities.search.open_advanced_search()


def test_vm_filter_without_user_input(appliance, vm_advanced_search, vms, subset_of_vms,
                                      expression_for_vms_subset):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    # Set up the filter
    vm_advanced_search.entities.search.advanced_search(expression_for_vms_subset)
    vm_advanced_search.flash.assert_no_error()
    vms_present = virtual_machines.get_all_vms(appliance, do_not_navigate=True)
    for vm in subset_of_vms:
        if vm not in vms_present:
            pytest.fail("Could not find VM {} after filtering!".format(vm))


@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_vm_filter_with_user_input(
        appliance, vm_advanced_search, vms, subset_of_vms, expression_for_vms_subset):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    vm_advanced_search.entities.search.advanced_search(
        "fill_field(Virtual Machine : Name, =)", {"Virtual Machine": vm}
    )
    vm_advanced_search.flash.assert_no_error()
    vms_present = virtual_machines.get_all_vms(appliance, do_not_navigate=True)
    if vm not in vms_present:
        pytest.fail("Could not find VM {} after filtering!".format(vm))


@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_vm_filter_with_user_input_and_cancellation(vm_advanced_search, vms, subset_of_vms,
                                                    expression_for_vms_subset):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    vm_advanced_search.entities.search.advanced_search(
        "fill_field(Virtual Machine : Name, =)",
        {"Virtual Machine": vm},
        cancel_on_user_filling=True
    )
    vm_advanced_search.flash.assert_no_error()


def test_vm_filter_save_cancel(vm_advanced_search, vms, subset_of_vms, expression_for_vms_subset):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up the filter
    vm_advanced_search.entities.search.save_filter(
        "fill_field(Virtual Machine : Name, =)",
        filter_name,
        cancel=True
    )
    vm_advanced_search.flash.assert_no_error()
    with pytest.raises(NoSuchElementException):
        vm_advanced_search.entities.search.load_filter(filter_name)  # does not exist


def test_vm_filter_save_and_load(appliance, request, vm_advanced_search, vms, subset_of_vms,
                                 expression_for_vms_subset):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    vm_advanced_search.entities.search.save_filter(
        "fill_field(Virtual Machine : Name, =)", filter_name)
    vm_advanced_search.flash.assert_no_error()
    vm_advanced_search.entities.search.reset_filter()

    vm_advanced_search.entities.search.load_filter(
        filter_name, fill_callback={"Virtual Machine": vm}, apply_filter=True)

    @request.addfinalizer
    def cleanup():
        vm_advanced_search.entities.search.load_filter(filter_name)
        vm_advanced_search.entities.search.delete_filter()

    vm_advanced_search.flash.assert_no_error()

    assert vm in virtual_machines.get_all_vms(appliance, do_not_navigate=True)


def test_vm_filter_save_and_cancel_load(request, vm_advanced_search):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up the filter
    vm_advanced_search.entities.search.save_filter(
        "fill_field(Virtual Machine : Name, =)", filter_name)

    @request.addfinalizer
    def cleanup():
        vm_advanced_search.entities.search.load_filter(filter_name)
        vm_advanced_search.entities.search.delete_filter()

    vm_advanced_search.flash.assert_no_error()
    vm_advanced_search.entities.search.reset_filter()

    vm_advanced_search.entities.search.load_filter(filter_name, cancel=True)
    vm_advanced_search.flash.assert_no_error()


def test_vm_filter_save_and_load_cancel(request, vms, subset_of_vms, vm_advanced_search):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    vm_advanced_search.entities.search.save_filter(
        "fill_field(Virtual Machine : Name, =)", filter_name)

    @request.addfinalizer
    def cleanup():
        vm_advanced_search.entities.search.load_filter(filter_name)
        vm_advanced_search.entities.search.delete_filter()

    vm_advanced_search.flash.assert_no_error()
    vm_advanced_search.entities.search.reset_filter()

    vm_advanced_search.entities.search.load_filter(
        filter_name,
        fill_callback={"Virtual Machine": vm},
        cancel_on_user_filling=True,
        apply_filter=True
    )
    vm_advanced_search.flash.assert_no_error()


def test_quick_search_without_vm_filter(appliance, request, vms, subset_of_vms):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    view = navigate_to(InfraVm, 'VMsOnly')
    view.flash.assert_no_error()
    vm = sample(subset_of_vms, 1)[0]
    # Make sure that we empty the regular view.entities.search field after the test
    request.addfinalizer(view.entities.search.clear_simple_search())
    # Filter this host only
    view.entities.search.simple_search(vm)
    view.flash.assert_no_error()
    # Check it is there
    all_vms_visible = virtual_machines.get_all_vms(appliance, do_not_navigate=True)
    assert len(all_vms_visible) == 1 and vm in all_vms_visible


def test_quick_search_with_vm_filter(
        vm_advanced_search, vms, subset_of_vms, appliance, expression_for_vms_subset):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    vm_advanced_search.entities.search.advanced_search(expression_for_vms_subset)
    vm_advanced_search.flash.assert_no_error()
    # Filter this host only
    chosen_vm = sample(subset_of_vms, 1)[0]
    vm_advanced_search.entities.search.simple_search(chosen_vm)
    vm_advanced_search.flash.assert_no_error()
    # Check it is there
    all_vms_visible = virtual_machines.get_all_vms(appliance, do_not_navigate=True)
    assert len(all_vms_visible) == 1 and chosen_vm in all_vms_visible


def test_can_delete_vm_filter(vm_advanced_search):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm_advanced_search.entities.search.save_filter(
        "fill_count(Virtual Machine.Files, >, 0)", filter_name)
    vm_advanced_search.flash.assert_no_error()
    vm_advanced_search.entities.search.reset_filter()
    vm_advanced_search.flash.assert_no_error()
    vm_advanced_search.entities.search.load_filter(filter_name)
    vm_advanced_search.flash.assert_no_error()
    if not vm_advanced_search.entities.search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    vm_advanced_search.flash.assert_no_error()


def test_delete_button_should_appear_after_save_vm(request, vm_advanced_search):
    """Delete button appears only after load, not after save

    Polarion:
        assignee: None
        initialEstimate: None
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm_advanced_search.entities.search.save_filter(
        "fill_count(Virtual Machine.Files, >, 0)", filter_name)

    @request.addfinalizer
    def cleanup():
        vm_advanced_search.entities.search.delete_filter()

    # Returns False if the button is not present
    if not vm_advanced_search.entities.search.delete_filter():
        pytest.fail("Could not delete filter right after saving!")


def test_cannot_delete_vm_filter_more_than_once(vm_advanced_search):
    """When Delete button appars, it does not want to go away

    Polarion:
        assignee: None
        initialEstimate: None
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm_advanced_search.entities.search.save_filter(
        "fill_count(Virtual Machine.Files, >, 0)", filter_name)
    # circumvent the thing happening in previous test
    vm_advanced_search.entities.search.load_filter(filter_name)
    # Delete once
    if not vm_advanced_search.entities.search.delete_filter():
        pytest.fail("Could not delete the filter even first time!")
    vm_advanced_search.flash.assert_no_error()
    # Try it second time
    assert not vm_advanced_search.entities.search.delete_filter(), 'Delete twice accepted!'
