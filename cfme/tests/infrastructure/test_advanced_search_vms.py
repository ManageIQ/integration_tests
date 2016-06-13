#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the search box in the VMs section"""
import fauxfactory
import pytest
from random import sample

from cfme.infrastructure import virtual_machines
from cfme.web_ui import search
from utils.providers import setup_a_provider
from cfme.web_ui.cfme_exception import (assert_no_cfme_exception,
    is_cfme_exception, cfme_exception_text)


@pytest.fixture(scope="module")
def vms():
    """Ensure the infra providers are set up and get list of vms"""
    try:
        setup_a_provider(prov_type="infra", required_keys="large")
    except Exception:
        pytest.skip("It's not possible to set up any providers, therefore skipping")
    pytest.sel.force_navigate("infra_vms")
    search.ensure_no_filter_applied()
    return virtual_machines.get_all_vms()


@pytest.yield_fixture(scope="function")
def close_search():
    """We must do this otherwise it's not possible to navigate after test!"""
    yield
    search.ensure_advanced_search_closed()


pytestmark = [pytest.mark.usefixtures("close_search"), pytest.mark.tier(3)]


@pytest.fixture(scope="module")
def subset_of_vms(vms):
    """We'll pick a host with median number of vms"""
    return sample(vms, 4)


@pytest.fixture(scope="module")
def expression_for_vms_subset(subset_of_vms):
    return ";select_first_expression;click_or;".join(
        ["fill_field(Virtual Machine : Name, =, {})".format(vm) for vm in subset_of_vms]
    )


def test_can_do_advanced_search():
    pytest.sel.force_navigate("infra_vms")
    assert search.is_advanced_search_possible(), "Cannot do advanced search here!"


@pytest.mark.requires("test_can_do_advanced_search")
def test_can_open_advanced_search():
    pytest.sel.force_navigate("infra_vms")
    search.ensure_advanced_search_open()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_without_user_input(vms, subset_of_vms, expression_for_vms_subset):
    pytest.sel.force_navigate("infra_vms")
    # Set up the filter
    search.fill_and_apply_filter(expression_for_vms_subset)
    assert_no_cfme_exception()
    vms_present = virtual_machines.get_all_vms(do_not_navigate=True)
    for vm in subset_of_vms:
        if vm not in vms_present:
            pytest.fail("Could not find VM {} after filtering!".format(vm))


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input(vms, subset_of_vms, expression_for_vms_subset):
    pytest.sel.force_navigate("infra_vms")
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    search.fill_and_apply_filter(
        "fill_field(Virtual Machine : Name, =)", {"Virtual Machine": vm}
    )
    assert_no_cfme_exception()
    vms_present = virtual_machines.get_all_vms(do_not_navigate=True)
    if vm not in vms_present:
        pytest.fail("Could not find VM {} after filtering!".format(vm))


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input_and_cancellation(vms, subset_of_vms, expression_for_vms_subset):
    pytest.sel.force_navigate("infra_vms")
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    search.fill_and_apply_filter(
        "fill_field(Virtual Machine : Name, =)",
        {"Virtual Machine": vm},
        cancel_on_user_filling=True
    )
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_cancel(vms, subset_of_vms, expression_for_vms_subset):
    pytest.sel.force_navigate("infra_vms")
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up the filter
    search.save_filter(
        "fill_field(Virtual Machine : Name, =)",
        filter_name,
        cancel=True
    )
    assert_no_cfme_exception()
    with pytest.raises(pytest.sel.NoSuchElementException):
        search.load_filter(filter_name)  # does not exist


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=[1273032])
def test_filter_save_and_load(request, vms, subset_of_vms, expression_for_vms_subset):
    pytest.sel.force_navigate("infra_vms")
    filter_name = fauxfactory.gen_alphanumeric()
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    search.save_filter("fill_field(Virtual Machine : Name, =)", filter_name)
    assert_no_cfme_exception()
    search.reset_filter()

    search.load_and_apply_filter(filter_name, fill_callback={"Virtual Machine": vm})
    assert_no_cfme_exception()
    request.addfinalizer(search.delete_filter)
    assert vm in virtual_machines.get_all_vms(do_not_navigate=True)


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=[1273032])
def test_filter_save_and_cancel_load(request):
    pytest.sel.force_navigate("infra_vms")
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up the filter
    search.save_filter("fill_field(Virtual Machine : Name, =)", filter_name)

    @request.addfinalizer
    def cleanup():
        pytest.sel.force_navigate("infra_vms")
        search.load_filter(filter_name)
        search.delete_filter()

    assert_no_cfme_exception()
    search.reset_filter()

    search.load_filter(filter_name, cancel=True)
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=[1273032])
def test_filter_save_and_load_cancel(request, vms, subset_of_vms):
    pytest.sel.force_navigate("infra_vms")
    filter_name = fauxfactory.gen_alphanumeric()
    vm = sample(subset_of_vms, 1)[0]
    # Set up the filter
    search.save_filter("fill_field(Virtual Machine : Name, =)", filter_name)

    @request.addfinalizer
    def cleanup():
        pytest.sel.force_navigate("infra_vms")
        search.load_filter(filter_name)
        search.delete_filter()

    assert_no_cfme_exception()
    search.reset_filter()

    search.load_and_apply_filter(
        filter_name,
        fill_callback={"Virtual Machine": vm},
        cancel_on_user_filling=True
    )
    assert_no_cfme_exception()


def test_quick_search_without_filter(request, vms, subset_of_vms):
    pytest.sel.force_navigate("infra_vms")
    search.ensure_no_filter_applied()
    assert_no_cfme_exception()
    vm = sample(subset_of_vms, 1)[0]
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(search.ensure_normal_search_empty)
    # Filter this host only
    search.normal_search(vm)
    assert_no_cfme_exception()
    # Check it is there
    all_vms_visible = virtual_machines.get_all_vms(do_not_navigate=True)
    assert len(all_vms_visible) == 1 and vm in all_vms_visible


@pytest.mark.requires("test_can_open_advanced_search")
def test_quick_search_with_filter(request, vms, subset_of_vms, expression_for_vms_subset):
    pytest.sel.force_navigate("infra_vms")
    search.fill_and_apply_filter(expression_for_vms_subset)
    assert_no_cfme_exception()
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(search.ensure_normal_search_empty)
    # Filter this host only
    chosen_vm = sample(subset_of_vms, 1)[0]
    search.normal_search(chosen_vm)
    assert_no_cfme_exception()
    # Check it is there
    all_vms_visible = virtual_machines.get_all_vms(do_not_navigate=True)
    assert len(all_vms_visible) == 1 and chosen_vm in all_vms_visible


@pytest.mark.meta(blockers=[1273032, 1320244])
def test_can_delete_filter():
    pytest.sel.force_navigate("infra_vms")
    filter_name = fauxfactory.gen_alphanumeric()
    search.save_filter("fill_count(Virtual Machine.Files, >, 0)", filter_name)
    assert_no_cfme_exception()
    search.reset_filter()
    assert_no_cfme_exception()
    search.load_filter(filter_name)
    assert_no_cfme_exception()
    if not search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    assert_no_cfme_exception()


@pytest.mark.meta(blockers=[1097150, 1273032, 1320244])
def test_delete_button_should_appear_after_save(request):
    """Delete button appears only after load, not after save"""
    pytest.sel.force_navigate("infra_vms")
    filter_name = fauxfactory.gen_alphanumeric()
    search.save_filter("fill_count(Virtual Machine.Files, >, 0)", filter_name)

    @request.addfinalizer
    def cleanup():
        pytest.sel.force_navigate("infra_vms")
        search.load_filter(filter_name)
        search.delete_filter()

    if not search.delete_filter():  # Returns False if the button is not present
        pytest.fail("Could not delete filter right after saving!")


@pytest.mark.meta(blockers=[1097150, 1273032, 1320244])
def test_cannot_delete_more_than_once(request, nuke_browser_after_test):
    """When Delete button appars, it does not want to go away"""
    pytest.sel.force_navigate("infra_vms")
    filter_name = fauxfactory.gen_alphanumeric()
    search.save_filter("fill_count(Virtual Machine.Files, >, 0)", filter_name)

    search.load_filter(filter_name)  # circumvent the thing happening in previous test
    # Delete once
    if not search.delete_filter():
        pytest.fail("Could not delete the filter even first time!")
    assert_no_cfme_exception()
    # Try it second time
    if search.delete_filter():  # If the button is there, it says True
        # This should not happen
        msg = "Delete twice accepted!"
        if is_cfme_exception():
            msg += " CFME Exception text: `{}`".format(cfme_exception_text())
        pytest.fail(msg)
