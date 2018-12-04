#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the view.entities.search box in the VMs section"""
from random import sample

import fauxfactory
import pytest
from widgetastic.exceptions import NoSuchElementException

from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider(classes=[InfraProvider], required_fields=['large'], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope="module")
def vms(appliance, provider):
    """Ensure the infra providers are set up and get list of vms"""
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    view.entities.search.remove_search_filters()
    return view.entities.all_entity_names  # surfs pages


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
def vm_view(appliance):
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    assert view.entities.search.is_advanced_search_possible, (
        "Cannot do advanced view.entities.search here!")
    yield view
    view.entities.search.remove_search_filters()


def test_can_open_vm_advanced_search(vm_view):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    vm_view.entities.search.open_advanced_search()


def test_vm_filter_without_user_input(appliance, vm_view, vms, subset_of_vms,
                                      expression_for_vms_subset):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # Set up the filter
    vm_view.entities.search.advanced_search(expression_for_vms_subset)
    vm_view.flash.assert_no_error()
    vms_present = vm_view.entities.entity_names
    for vm in subset_of_vms:
        assert vm in vms_present, "Could not find VM {} after filtering!".format(vm)


@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_vm_filter_with_user_input(
        appliance, vm_view, vms, subset_of_vms, expression_for_vms_subset):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    vm_view.entities.search.advanced_search(
        "fill_field(Virtual Machine : Name, =)", {"Virtual Machine": vm}
    )
    vm_view.flash.assert_no_error()
    assert vm in vm_view.entities.entity_names, "Could not find VM {} after filtering!".format(vm)


@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_vm_filter_with_user_input_and_cancellation(vm_view, vms, subset_of_vms,
                                                    expression_for_vms_subset):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    vm_view.entities.search.advanced_search(
        "fill_field(Virtual Machine : Name, =)",
        {"Virtual Machine": vm},
        cancel_on_user_filling=True
    )
    vm_view.flash.assert_no_error()


def test_vm_filter_save_cancel(vm_view, vms, subset_of_vms, expression_for_vms_subset):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up the filter
    vm_view.entities.search.save_filter(
        "fill_field(Virtual Machine : Name, =)",
        filter_name,
        cancel=True
    )
    vm_view.flash.assert_no_error()
    with pytest.raises(NoSuchElementException):
        vm_view.entities.search.load_filter(filter_name)  # does not exist


def test_vm_filter_save_and_load(appliance, request, vm_view, vms, subset_of_vms,
                                 expression_for_vms_subset):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    vm_view.entities.search.save_filter(
        "fill_field(Virtual Machine : Name, =)", filter_name)
    vm_view.flash.assert_no_error()
    vm_view.entities.search.reset_filter()

    vm_view.entities.search.load_filter(
        filter_name, fill_callback={"Virtual Machine": vm}, apply_filter=True)

    @request.addfinalizer
    def cleanup():
        vm_view.entities.search.load_filter(filter_name)
        vm_view.entities.search.delete_filter()

    vm_view.flash.assert_no_error()

    assert vm in vm_view.entities.entity_names


def test_vm_filter_save_and_cancel_load(request, vm_view):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up the filter
    vm_view.entities.search.save_filter(
        "fill_field(Virtual Machine : Name, =)", filter_name)

    @request.addfinalizer
    def cleanup():
        vm_view.entities.search.load_filter(filter_name)
        vm_view.entities.search.delete_filter()

    vm_view.flash.assert_no_error()
    vm_view.entities.search.reset_filter()

    vm_view.entities.search.load_filter(filter_name, cancel=True)
    vm_view.flash.assert_no_error()


def test_vm_filter_save_and_load_cancel(request, vms, subset_of_vms, vm_view):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    vm_view.entities.search.save_filter(
        "fill_field(Virtual Machine : Name, =)", filter_name)

    @request.addfinalizer
    def cleanup():
        vm_view.entities.search.load_filter(filter_name)
        vm_view.entities.search.delete_filter()

    vm_view.flash.assert_no_error()
    vm_view.entities.search.reset_filter()

    vm_view.entities.search.load_filter(
        filter_name,
        fill_callback={"Virtual Machine": vm},
        cancel_on_user_filling=True,
        apply_filter=True
    )
    vm_view.flash.assert_no_error()


def test_quick_search_without_vm_filter(appliance, request, vms, subset_of_vms):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    view.flash.assert_no_error()
    vm = sample(subset_of_vms, 1)[0]
    # Make sure that we empty the regular view.entities.search field after the test
    request.addfinalizer(view.entities.search.clear_simple_search())
    # Filter this host only
    view.entities.search.simple_search(vm)
    view.flash.assert_no_error()
    # Check it is there
    all_vms_visible = [entity.name for entity in view.entities.get_all(surf_pages=False)]
    assert len(all_vms_visible) == 1 and vm in all_vms_visible


def test_quick_search_with_vm_filter(
        vm_view, vms, subset_of_vms, appliance, expression_for_vms_subset):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    vm_view.entities.search.advanced_search(expression_for_vms_subset)
    vm_view.flash.assert_no_error()
    # Filter this host only
    chosen_vm = sample(subset_of_vms, 1)[0]
    vm_view.entities.search.simple_search(chosen_vm)
    vm_view.flash.assert_no_error()
    # Check it is there
    all_vms_visible = vm_view.entities.entity_names
    assert len(all_vms_visible) == 1 and chosen_vm in all_vms_visible


def test_can_delete_vm_filter(vm_view):
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm_view.entities.search.save_filter(
        "fill_count(Virtual Machine.Files, >, 0)", filter_name)
    vm_view.flash.assert_no_error()
    vm_view.entities.search.reset_filter()
    vm_view.flash.assert_no_error()
    vm_view.entities.search.load_filter(filter_name)
    vm_view.flash.assert_no_error()
    if not vm_view.entities.search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    vm_view.flash.assert_no_error()


def test_delete_button_should_appear_after_save_vm(request, vm_view):
    """Delete button appears only after load, not after save

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm_view.entities.search.save_filter(
        "fill_count(Virtual Machine.Files, >, 0)", filter_name)

    @request.addfinalizer
    def cleanup():
        vm_view.entities.search.delete_filter()

    # Returns False if the button is not present
    if not vm_view.entities.search.delete_filter():
        pytest.fail("Could not delete filter right after saving!")


def test_cannot_delete_vm_filter_more_than_once(vm_view):
    """When Delete button appars, it does not want to go away

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    vm_view.entities.search.save_filter(
        "fill_count(Virtual Machine.Files, >, 0)", filter_name)
    # circumvent the thing happening in previous test
    vm_view.entities.search.load_filter(filter_name)
    # Delete once
    if not vm_view.entities.search.delete_filter():
        pytest.fail("Could not delete the filter even first time!")
    vm_view.flash.assert_no_error()
    # Try it second time
    assert not vm_view.entities.search.delete_filter(), 'Delete twice accepted!'
