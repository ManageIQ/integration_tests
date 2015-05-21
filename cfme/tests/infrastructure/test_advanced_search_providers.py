# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the search box in the Provider section

It does not check for filtering results so far."""
import fauxfactory
import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import host
from utils.providers import setup_a_provider
from cfme.web_ui import search
from cfme.web_ui.cfme_exception import (assert_no_cfme_exception,
    is_cfme_exception, cfme_exception_text)


@pytest.fixture(scope="module")
def providers():
    """Ensure the infra providers are set up and get list of hosts"""
    try:
        setup_a_provider(prov_type="infra")
    except Exception:
        pytest.skip("It's not possible to set up any providers, therefore skipping")
    sel.force_navigate("infrastructure_providers")
    search.ensure_no_filter_applied()


@pytest.fixture(scope="module")
def hosts_with_vm_count(hosts):
    """Returns a list of tuples (hostname, vm_count)"""
    hosts_with_vm_count = []
    for host_name in hosts:
        hosts_with_vm_count.append((host_name, int(host.find_quadicon(host_name, True).no_vm)))
    return sorted(hosts_with_vm_count, key=lambda tup: tup[1])


@pytest.yield_fixture(scope="function")
def close_search():
    """We must do this otherwise it's not possible to navigate after test!"""
    yield
    search.ensure_advanced_search_closed()


pytestmark = [pytest.mark.usefixtures("close_search")]


def test_can_do_advanced_search():
    sel.force_navigate("infrastructure_providers")
    assert search.is_advanced_search_possible(), "Cannot do advanced search here!"


@pytest.mark.requires("test_can_do_advanced_search")
def test_can_open_advanced_search():
    sel.force_navigate("infrastructure_providers")
    search.ensure_advanced_search_open()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_without_user_input(providers):
    sel.force_navigate("infrastructure_providers")
    # Set up the filter
    search.fill_and_apply_filter("fill_count(Infrastructure Provider.VMs, >=, 0)")
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input(providers):
    sel.force_navigate("infrastructure_providers")
    # Set up the filter
    search.fill_and_apply_filter("fill_count(Infrastructure Provider.VMs, >=)", {"COUNT": 0})
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input_and_cancellation(providers):
    sel.force_navigate("infrastructure_providers")
    # Set up the filter
    search.fill_and_apply_filter(
        "fill_count(Infrastructure Provider.VMs, >=)", {"COUNT": 0},
        cancel_on_user_filling=True
    )
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=[1168336])
def test_filter_save_cancel(request, providers, ssh_client):
    sel.force_navigate("infrastructure_providers")
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up finalizer
    request.addfinalizer(
        lambda: ssh_client.run_rails_command(
            "\"MiqSearch.where(:description => {}).first.delete\"".format(repr(filter_name))))
    # Try save filter
    search.save_filter("fill_count(Infrastructure Provider.VMs, >)", filter_name, cancel=True)
    assert_no_cfme_exception()
    with pytest.raises(sel.NoSuchElementException):
        search.load_filter(filter_name)  # does not exist


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=[1168336])
def test_filter_save_and_load(request, providers, ssh_client):
    sel.force_navigate("infrastructure_providers")
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up finalizer
    request.addfinalizer(
        lambda: ssh_client.run_rails_command(
            "\"MiqSearch.where(:description => {}).first.delete\"".format(repr(filter_name))))
    # Try save filter
    search.save_filter("fill_count(Infrastructure Provider.VMs, >)", filter_name)
    assert_no_cfme_exception()
    search.reset_filter()

    search.load_and_apply_filter(filter_name, fill_callback={"COUNT": 0})
    assert_no_cfme_exception()
    request.addfinalizer(search.delete_filter)


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=[1168336])
def test_filter_save_and_cancel_load(request, providers, ssh_client):
    sel.force_navigate("infrastructure_providers")
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up finalizer
    request.addfinalizer(
        lambda: ssh_client.run_rails_command(
            "\"MiqSearch.where(:description => {}).first.delete\"".format(repr(filter_name))))
    # Try save filter
    search.save_filter("fill_count(Infrastructure Provider.VMs, >)", filter_name)

    def cleanup():
        sel.force_navigate("infrastructure_providers")
        search.load_filter(filter_name)
        search.delete_filter()

    request.addfinalizer(cleanup)
    assert_no_cfme_exception()
    search.reset_filter()

    search.load_filter(filter_name, cancel=True)
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=[1168336])
def test_filter_save_and_load_cancel(request, providers, ssh_client):
    sel.force_navigate("infrastructure_providers")
    filter_name = fauxfactory.gen_alphanumeric()
    # Set up finalizer
    request.addfinalizer(
        lambda: ssh_client.run_rails_command(
            "\"MiqSearch.where(:description => {}).first.delete\"".format(repr(filter_name))))
    # Try save filter
    search.save_filter("fill_count(Infrastructure Provider.VMs, >)", filter_name)

    def cleanup():
        sel.force_navigate("infrastructure_providers")
        search.load_filter(filter_name)
        search.delete_filter()

    request.addfinalizer(cleanup)
    assert_no_cfme_exception()
    search.reset_filter()

    search.load_and_apply_filter(
        filter_name,
        fill_callback={"COUNT": 0},
        cancel_on_user_filling=True
    )
    assert_no_cfme_exception()


def test_quick_search_without_filter(request, providers):
    sel.force_navigate("infrastructure_providers")
    search.ensure_no_filter_applied()
    assert_no_cfme_exception()
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(search.ensure_normal_search_empty)
    # Filter this host only
    search.normal_search(fauxfactory.gen_alphanumeric())
    assert_no_cfme_exception()


def test_quick_search_with_filter(request, providers):
    sel.force_navigate("infrastructure_providers")
    search.fill_and_apply_filter("fill_count(Infrastructure Provider.VMs, >=, 0)")
    assert_no_cfme_exception()
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(search.ensure_normal_search_empty)
    # Filter this host only
    search.normal_search(fauxfactory.gen_alphanumeric())
    assert_no_cfme_exception()


@pytest.mark.meta(blockers=[1168336])
def test_can_delete_filter():
    sel.force_navigate("infrastructure_providers")
    filter_name = fauxfactory.gen_alphanumeric()
    search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)
    assert_no_cfme_exception()
    search.reset_filter()
    assert_no_cfme_exception()
    search.load_filter(filter_name)
    assert_no_cfme_exception()
    if not search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    assert_no_cfme_exception()


@pytest.mark.meta(blockers=[1097150, 1168336])
def test_delete_button_should_appear_after_save(request):
    """Delete button appears only after load, not after save"""
    sel.force_navigate("infrastructure_providers")
    filter_name = fauxfactory.gen_alphanumeric()
    search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)

    def cleanup():
        sel.force_navigate("infrastructure_providers")
        search.load_filter(filter_name)
        search.delete_filter()

    request.addfinalizer(cleanup)
    if not search.delete_filter():  # Returns False if the button is not present
        pytest.fail("Could not delete filter right after saving!")


@pytest.mark.meta(blockers=[1097150])
def test_cannot_delete_more_than_once(request):
    """When Delete button appars, it does not want to go away"""
    sel.force_navigate("infrastructure_providers")
    filter_name = fauxfactory.gen_alphanumeric()
    search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)

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
