# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the search box in the Hosts section"""
import pytest
from itertools import dropwhile

from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import host
from utils.providers import setup_a_provider
from cfme.web_ui import search
from cfme.web_ui.cfme_exception import (assert_no_cfme_exception,
    is_cfme_exception, cfme_exception_text)
from utils.randomness import generate_random_string
from utils.version import since_date_or_version


@pytest.fixture(scope="module")
def hosts():
    """Ensure the infra providers are set up and get list of hosts"""
    try:
        setup_a_provider(prov_type="infra")
    except Exception:
        pytest.skip("It's not possible to set up any providers, therefore skipping")
    sel.force_navigate("infrastructure_hosts")
    search.ensure_no_filter_applied()
    return host.get_all_hosts()


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


def get_expression(user_input=False, op=">"):
    if since_date_or_version(date="2015-04-30", version="5.4.0.0.25"):
        expression = "fill_count(Host / Node.VMs, %s" % op
    else:
        expression = "fill_count(Host.VMs, %s" % op
    if user_input:
        return expression + ")"
    else:
        return expression + ", %d)"


pytestmark = [pytest.mark.usefixtures("close_search")]


@pytest.fixture(scope="module")
def host_with_median_vm(hosts_with_vm_count):
    """We'll pick a host with median number of vms"""
    return hosts_with_vm_count[len(hosts_with_vm_count) // 2]


def test_can_do_advanced_search():
    sel.force_navigate("infrastructure_hosts")
    assert search.is_advanced_search_possible(), "Cannot do advanced search here!"


@pytest.mark.requires("test_can_do_advanced_search")
def test_can_open_advanced_search():
    sel.force_navigate("infrastructure_hosts")
    search.ensure_advanced_search_open()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_without_user_input(hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    median_host, median_vm_count = host_with_median_vm
    # We will filter out hosts with less than median VMs
    more_than_median_hosts = list(dropwhile(lambda h: h[1] <= median_vm_count, hosts_with_vm_count))
    # Set up the filter
    search.fill_and_apply_filter(get_expression(False) % median_vm_count)
    assert_no_cfme_exception()
    assert len(more_than_median_hosts) == len(host.get_all_hosts(do_not_navigate=True))


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input(hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    median_host, median_vm_count = host_with_median_vm
    # We will filter out hosts with less than median VMs
    more_than_median_hosts = list(dropwhile(lambda h: h[1] <= median_vm_count, hosts_with_vm_count))

    # Set up the filter
    search.fill_and_apply_filter(get_expression(True), {"COUNT": median_vm_count})
    assert_no_cfme_exception()
    assert len(more_than_median_hosts) == len(host.get_all_hosts(do_not_navigate=True))


@pytest.mark.requires("test_can_open_advanced_search")
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input_and_cancellation(hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    median_host, median_vm_count = host_with_median_vm

    # Set up the filter
    search.fill_and_apply_filter(
        get_expression(True),
        {"COUNT": median_vm_count},
        cancel_on_user_filling=True
    )
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_cancel(hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    median_host, median_vm_count = host_with_median_vm
    filter_name = generate_random_string()
    # Try save filter
    search.save_filter(get_expression(True), filter_name, cancel=True)
    assert_no_cfme_exception()
    with pytest.raises(sel.NoSuchElementException):
        search.load_filter(filter_name)  # does not exist


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_load(request, hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    median_host, median_vm_count = host_with_median_vm
    # We will filter out hosts with less than median VMs
    more_than_median_hosts = list(dropwhile(lambda h: h[1] <= median_vm_count, hosts_with_vm_count))

    filter_name = generate_random_string()
    # Try save filter
    search.save_filter(get_expression(True), filter_name)
    assert_no_cfme_exception()
    search.reset_filter()

    search.load_and_apply_filter(filter_name, fill_callback={"COUNT": median_vm_count})
    assert_no_cfme_exception()
    request.addfinalizer(search.delete_filter)
    assert len(more_than_median_hosts) == len(host.get_all_hosts(do_not_navigate=True))


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_cancel_load(request, hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    median_host, median_vm_count = host_with_median_vm

    filter_name = generate_random_string()
    # Try save filter
    search.save_filter(get_expression(True), filter_name)

    def cleanup():
        sel.force_navigate("infrastructure_hosts")
        search.load_filter(filter_name)
        search.delete_filter()

    request.addfinalizer(cleanup)
    assert_no_cfme_exception()
    search.reset_filter()

    search.load_filter(filter_name, cancel=True)
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_load_cancel(request, hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    median_host, median_vm_count = host_with_median_vm

    filter_name = generate_random_string()
    # Try save filter
    search.save_filter(get_expression(True), filter_name)

    def cleanup():
        sel.force_navigate("infrastructure_hosts")
        search.load_filter(filter_name)
        search.delete_filter()

    request.addfinalizer(cleanup)
    assert_no_cfme_exception()
    search.reset_filter()

    search.load_and_apply_filter(
        filter_name,
        fill_callback={"COUNT": median_vm_count},
        cancel_on_user_filling=True
    )
    assert_no_cfme_exception()


def test_quick_search_without_filter(request, hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    search.ensure_no_filter_applied()
    assert_no_cfme_exception()
    median_host, median_vm_count = host_with_median_vm
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(search.ensure_normal_search_empty)
    # Filter this host only
    search.normal_search(median_host)
    assert_no_cfme_exception()
    # Check it is there
    all_hosts_visible = host.get_all_hosts(do_not_navigate=True)
    assert len(all_hosts_visible) == 1 and median_host in all_hosts_visible


def test_quick_search_with_filter(request, hosts, hosts_with_vm_count, host_with_median_vm):
    sel.force_navigate("infrastructure_hosts")
    median_host, median_vm_count = host_with_median_vm
    search.fill_and_apply_filter(
        get_expression(False, ">=") % median_vm_count
    )
    assert_no_cfme_exception()
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(search.ensure_normal_search_empty)
    # Filter this host only
    search.normal_search(median_host)
    assert_no_cfme_exception()
    # Check it is there
    all_hosts_visible = host.get_all_hosts(do_not_navigate=True)
    assert len(all_hosts_visible) == 1 and median_host in all_hosts_visible


def test_can_delete_filter():
    sel.force_navigate("infrastructure_hosts")
    filter_name = generate_random_string()
    search.save_filter(get_expression(False) % 0, filter_name)
    assert_no_cfme_exception()
    search.reset_filter()
    assert_no_cfme_exception()
    search.load_filter(filter_name)
    assert_no_cfme_exception()
    if not search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    assert_no_cfme_exception()


@pytest.mark.meta(blockers=[1097150])
def test_delete_button_should_appear_after_save(request):
    """Delete button appears only after load, not after save"""
    sel.force_navigate("infrastructure_hosts")
    filter_name = generate_random_string()
    search.save_filter(get_expression(False) % 0, filter_name)

    def cleanup():
        sel.force_navigate("infrastructure_hosts")
        search.load_filter(filter_name)
        search.delete_filter()

    request.addfinalizer(cleanup)
    if not search.delete_filter():  # Returns False if the button is not present
        pytest.fail("Could not delete filter right after saving!")


@pytest.mark.meta(blockers=[1097150])
def test_cannot_delete_more_than_once(request):
    """When Delete button appars, it does not want to go away"""
    sel.force_navigate("infrastructure_hosts")
    filter_name = generate_random_string()
    search.save_filter(get_expression(False) % 0, filter_name)

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
