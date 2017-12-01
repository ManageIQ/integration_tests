# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the search box in the Hosts section"""
import fauxfactory
import pytest
from itertools import dropwhile
from widgetastic.exceptions import NoSuchElementException

from cfme.web_ui.cfme_exception import is_cfme_exception, cfme_exception_text
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [pytest.mark.tier(3)]


@pytest.fixture(scope='module')
def host_collection(appliance):
    return appliance.collections.hosts


@pytest.fixture(scope="function")
def hosts(infra_provider, host_collection):
    view = navigate_to(host_collection, 'All')
    view.entities.search.remove_search_filters()
    return host_collection.all(infra_provider)


@pytest.fixture(scope="function")
def hosts_with_vm_count(hosts, host_collection):
    """Returns a list of tuples (hostname, vm_count)"""
    hosts_with_vm_count = []
    view = navigate_to(host_collection, 'All')
    view.toolbar.view_selector.select("Grid View")
    for host in hosts:
        entity = view.entities.get_entity(name=host.name)
        hosts_with_vm_count.append((host.name, entity.data['no_vm']))
    return sorted(hosts_with_vm_count, key=lambda tup: tup[1])


def get_expression(user_input=False, op=">"):
    expression = "fill_count(Host / Node.VMs, {}".format(op)
    if user_input:
        return expression + ")"
    else:
        return expression + ", {})"


@pytest.fixture(scope="function")
def host_with_median_vm(hosts_with_vm_count):
    """We'll pick a host with median number of vms"""
    return hosts_with_vm_count[len(hosts_with_vm_count) // 2]


@pytest.fixture(scope="function")
def hosts_advanced_search(host_collection):
    view = navigate_to(host_collection, 'All')
    assert view.entities.search.is_advanced_search_possible, "Cannot do advanced search here!"
    yield view
    view.entities.search.remove_search_filters()


def test_can_open_advanced_search(hosts_advanced_search):
    hosts_advanced_search.entities.search.open_advanced_search()


def test_filter_without_user_input(host_collection, hosts, hosts_with_vm_count,
                                   host_with_median_vm, infra_provider, hosts_advanced_search):
    median_host, median_vm_count = host_with_median_vm
    # We will filter out hosts with less than median VMs
    more_than_median_hosts = list(dropwhile(lambda h: h[1] <= median_vm_count, hosts_with_vm_count))
    # Set up the filter
    hosts_advanced_search.entities.search.advanced_search(get_expression(False).format(
        median_vm_count))
    hosts_advanced_search.flash.assert_no_error()
    assert len(more_than_median_hosts) == len(host_collection.all(infra_provider))


@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input(host_collection, hosts, hosts_with_vm_count, host_with_median_vm,
                                infra_provider, hosts_advanced_search):
    median_host, median_vm_count = host_with_median_vm
    # We will filter out hosts with less than median VMs
    more_than_median_hosts = list(dropwhile(lambda h: h[1] <= median_vm_count, hosts_with_vm_count))

    # Set up the filter
    hosts_advanced_search.entities.search.advanced_search(get_expression(True),
                                                          {"COUNT": median_vm_count})
    hosts_advanced_search.flash.assert_no_error()
    assert len(more_than_median_hosts) == len(host_collection.all(infra_provider))


@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2322"])
def test_filter_with_user_input_and_cancellation(host_collection, hosts, hosts_with_vm_count,
                                                 host_with_median_vm, hosts_advanced_search):
    median_host, median_vm_count = host_with_median_vm

    # Set up the filter
    hosts_advanced_search.entities.search.advanced_search(
        get_expression(True),
        {"COUNT": median_vm_count},
        cancel_on_user_filling=True
    )
    hosts_advanced_search.flash.assert_no_error()


def test_filter_save_cancel(hosts_advanced_search, hosts, hosts_with_vm_count, host_with_median_vm):
    median_host, median_vm_count = host_with_median_vm
    filter_name = fauxfactory.gen_alphanumeric()
    # Try save filter
    hosts_advanced_search.entities.search.save_filter(get_expression(True),
                                                      filter_name,
                                                      cancel=True)
    hosts_advanced_search.flash.assert_no_error()
    with pytest.raises(NoSuchElementException):
        hosts_advanced_search.entities.search.load_filter(filter_name)  # does not exist


def test_filter_save_and_load(host_collection, request, hosts, hosts_with_vm_count,
                              host_with_median_vm, infra_provider, hosts_advanced_search):
    median_host, median_vm_count = host_with_median_vm
    # We will filter out hosts with less than median VMs
    more_than_median_hosts = list(dropwhile(lambda h: h[1] <= median_vm_count, hosts_with_vm_count))

    filter_name = fauxfactory.gen_alphanumeric()
    # Try save filter
    hosts_advanced_search.entities.search.save_filter(get_expression(True), filter_name)
    hosts_advanced_search.flash.assert_no_error()
    hosts_advanced_search.entities.search.reset_filter()

    hosts_advanced_search.entities.search.load_filter(
        filter_name, fill_callback={"COUNT": median_vm_count}, apply_filter=True)
    hosts_advanced_search.flash.assert_no_error()
    request.addfinalizer(hosts_advanced_search.entities.search.delete_filter)
    assert len(more_than_median_hosts) == len(host_collection.all(infra_provider))


def test_filter_save_and_cancel_load(host_collection, request, hosts, hosts_with_vm_count,
                                     host_with_median_vm, hosts_advanced_search):
    median_host, median_vm_count = host_with_median_vm

    filter_name = fauxfactory.gen_alphanumeric()
    # Try save filter
    hosts_advanced_search.entities.search.save_filter(get_expression(True), filter_name)

    @request.addfinalizer
    def cleanup():
        hosts_advanced_search.entities.search.load_filter(filter_name)
        hosts_advanced_search.entities.search.delete_filter()

    hosts_advanced_search.flash.assert_no_error()
    hosts_advanced_search.entities.search.reset_filter()

    hosts_advanced_search.entities.search.load_filter(filter_name, cancel=True)
    hosts_advanced_search.flash.assert_no_error()


def test_filter_save_and_load_cancel(hosts_advanced_search, request, hosts, hosts_with_vm_count,
                                     host_with_median_vm):
    median_host, median_vm_count = host_with_median_vm

    filter_name = fauxfactory.gen_alphanumeric()
    # Try save filter
    hosts_advanced_search.entities.search.save_filter(get_expression(True), filter_name)

    @request.addfinalizer
    def cleanup():
        hosts_advanced_search.entities.search.load_filter(filter_name)
        hosts_advanced_search.entities.search.delete_filter()

    hosts_advanced_search.flash.assert_no_error()
    hosts_advanced_search.entities.search.reset_filter()

    hosts_advanced_search.entities.search.load_filter(
        filter_name,
        fill_callback={"COUNT": median_vm_count},
        cancel_on_user_filling=True,
        apply_filter=True
    )
    hosts_advanced_search.flash.assert_no_error()


def test_quick_search_without_filter(host_collection, request, hosts, hosts_with_vm_count,
                                     host_with_median_vm, infra_provider):
    view = navigate_to(host_collection, 'All')
    view.entities.search.remove_search_filters()
    view.flash.assert_no_error()
    median_host, median_vm_count = host_with_median_vm
    # Filter this host only
    view.entities.search.simple_search(median_host)
    request.addfinalizer(view.entities.search.clear_simple_search)
    view.flash.assert_no_error()
    # Check it is there
    all_hosts_visible = host_collection.all(infra_provider)
    assert len(all_hosts_visible) == 1 and median_host in [host.name for host in all_hosts_visible]


def test_quick_search_with_filter(host_collection, request, hosts, hosts_with_vm_count,
                                  host_with_median_vm, infra_provider):
    view = navigate_to(host_collection, 'All')
    median_host, median_vm_count = host_with_median_vm
    view.entities.search.advanced_search(get_expression(False, ">=").format(median_vm_count))
    view.flash.assert_no_error()
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(view.entities.search.clear_simple_search)
    # Filter this host only
    view.entities.search.simple_search(median_host)
    view.flash.assert_no_error()
    # Check it is there
    all_hosts_visible = host_collection.all(infra_provider)
    assert len(all_hosts_visible) == 1 and median_host in [host.name for host in all_hosts_visible]


def test_can_delete_filter(host_collection, hosts_advanced_search):
    filter_name = fauxfactory.gen_alphanumeric()
    hosts_advanced_search.entities.search.save_filter(get_expression(False).format(0), filter_name)
    hosts_advanced_search.flash.assert_no_error()
    hosts_advanced_search.entities.search.reset_filter()
    hosts_advanced_search.flash.assert_no_error()
    hosts_advanced_search.entities.search.load_filter(filter_name)
    hosts_advanced_search.flash.assert_no_error()
    if not hosts_advanced_search.entities.search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    hosts_advanced_search.flash.assert_no_error()


def test_delete_button_should_appear_after_save(host_collection, hosts_advanced_search, request):
    """Delete button appears only after load, not after save"""
    filter_name = fauxfactory.gen_alphanumeric()
    hosts_advanced_search.entities.search.save_filter(get_expression(False).format(0), filter_name)

    @request.addfinalizer
    def cleanup():
        hosts_advanced_search.entities.search.load_filter(filter_name)
        hosts_advanced_search.entities.search.delete_filter()

    if not hosts_advanced_search.entities.search.delete_filter():
        # Returns False if the button is not present
        pytest.fail("Could not delete filter right after saving!")


def test_cannot_delete_more_than_once(host_collection, hosts_advanced_search,
                                      nuke_browser_after_test):
    """When Delete button appars, it does not want to go away"""
    filter_name = fauxfactory.gen_alphanumeric()
    hosts_advanced_search.entities.search.save_filter(get_expression(False).format(0), filter_name)
    # circumvent the thing happening in previous test
    hosts_advanced_search.entities.search.load_filter(filter_name)
    # Delete once
    if not hosts_advanced_search.entities.search.delete_filter():
        pytest.fail("Could not delete the filter even first time!")
    hosts_advanced_search.flash.assert_no_error()
    # Try it second time
    # If the button is there, it says True
    if hosts_advanced_search.entities.search.delete_filter():
        # This should not happen
        msg = "Delete twice accepted!"
        if is_cfme_exception():
            msg += " CFME Exception text: `{}`".format(cfme_exception_text())
        pytest.fail(msg)
