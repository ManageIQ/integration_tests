# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the search box in the Provider section

It does not check for filtering results so far."""
import fauxfactory
import pytest
from selenium.common.exceptions import NoSuchElementException

from cfme.infrastructure import host
from cfme.infrastructure.provider import InfraProvider
# TODO: we should not call out to utils here, but maybe rather have an infra setup provider fixture
from fixtures.pytest_store import store
from utils.providers import setup_a_provider
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger
from cfme.web_ui import search
from cfme.web_ui.search import DisabledButtonException
from cfme.web_ui.cfme_exception import (assert_no_cfme_exception,
    is_cfme_exception, cfme_exception_text)


pytestmark = [pytest.mark.usefixtures("setup_cleanup_search"), pytest.mark.tier(3)]


@pytest.fixture(scope="module")
def single_provider():
    """Ensure the infra provider is setup"""
    try:
        return setup_a_provider(prov_class="infra")
    except Exception as ex:
        pytest.skip("Exception while setting up providers, therefore skipping: {}".format(ex))


@pytest.fixture(scope="module")
def hosts_with_vm_count(hosts):
    """Returns a list of tuples (hostname, vm_count)"""
    hosts_with_vm_count = []
    for host_name in hosts:
        hosts_with_vm_count.append((host_name, int(host.find_quadicon(host_name, True).no_vm)))
    return sorted(hosts_with_vm_count, key=lambda tup: tup[1])


@pytest.yield_fixture(scope="function")
def setup_cleanup_search():
    """Navigate to InfraProvider, clear search on setup and teardown"""
    navigate_to(InfraProvider, 'All')
    search.ensure_no_filter_applied()

    yield

    # cleanup after test
    search.ensure_no_filter_applied()
    search.ensure_advanced_search_closed()


@pytest.yield_fixture(scope="function")
def rails_delete_filter(request):
    """Introspect a function bound filter_name and use ssh_client and rails to delete it"""
    # No pre-test, just cleanup after yield
    yield

    filter_name = getattr(request.function, "filter_name", None)
    logger.debug('rails_delete_filter: calling rails to delete filter: {}'.format(filter_name))
    if filter_name:
        try:
            store.current_appliance.ssh_client.run_rails_command(
                '"MiqSearch.where(:description => {}).first.delete"'.format(repr(filter_name)))
        except Exception as ex:
            logger.warning('rails_delete_filter: exception during delete. {}'.format(ex))
            pass
    else:
        logger.warning('rails_delete_filter: failed to get filter_name')


def test_can_do_advanced_search(single_provider):
    navigate_to(InfraProvider, 'All')
    assert search.is_advanced_search_possible(), "Cannot do advanced search here!"


@pytest.mark.requires("test_can_do_advanced_search")
def test_can_open_advanced_search(single_provider):
    navigate_to(InfraProvider, 'All')
    search.ensure_advanced_search_open()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_without_user_input(single_provider):
    # Set up the filter
    search.fill_and_apply_filter("fill_count(Infrastructure Provider.VMs, >=, 0)")
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_with_user_input(single_provider):
    # Set up the filter
    logger.debug('DEBUG: test_with_user_input: fill and apply')
    search.fill_and_apply_filter("fill_count(Infrastructure Provider.VMs, >=)",
                                 fill_callback={"COUNT": 0})
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_with_user_input_and_cancellation(single_provider):
    # Set up the filter
    search.fill_and_apply_filter(
        "fill_count(Infrastructure Provider.VMs, >=)", fill_callback={"COUNT": 0},
        cancel_on_user_filling=True
    )
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_cancel(single_provider, rails_delete_filter):
    # bind filter_name to the function for fixture cleanup
    test_filter_save_cancel.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(test_filter_save_cancel.filter_name))

    # Try save filter
    assert search.save_filter("fill_count(Infrastructure Provider.VMs, >)",
                              test_filter_save_cancel.filter_name, cancel=True)
    assert_no_cfme_exception()

    assert search.reset_filter()
    # Exception depends on system state - Load button will be disabled if there are no saved filters
    with pytest.raises((DisabledButtonException, NoSuchElementException)):
        search.load_filter(saved_filter=test_filter_save_cancel.filter_name)


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_load(single_provider, rails_delete_filter):
    # bind filter_name to the function for fixture cleanup
    test_filter_save_and_load.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(test_filter_save_and_load.filter_name))

    # Save filter
    assert search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)",
                              test_filter_save_and_load.filter_name)
    assert_no_cfme_exception()

    # Reset filter
    assert search.reset_filter()

    # Load filter
    assert search.load_filter(test_filter_save_and_load.filter_name)
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_cancel_load(single_provider, rails_delete_filter):
    # bind filter_name to the function for fixture cleanup
    test_filter_save_and_cancel_load.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(test_filter_save_and_cancel_load.filter_name))

    # Save filter
    assert search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)",
                              test_filter_save_and_cancel_load.filter_name)
    assert_no_cfme_exception()

    # Reset Filter
    assert search.reset_filter()

    # Load and cancel
    assert search.load_filter(test_filter_save_and_cancel_load.filter_name, cancel=True)
    assert_no_cfme_exception()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_cancel_load_with_user_input(single_provider, rails_delete_filter):
    # bind filter_name to the function for fixture cleanup
    test_filter_save_and_cancel_load_with_user_input.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(
        test_filter_save_and_cancel_load_with_user_input.filter_name))

    # Save filter
    assert search.save_filter("fill_count(Infrastructure Provider.VMs, >)",
                              test_filter_save_and_cancel_load_with_user_input.filter_name)
    assert_no_cfme_exception()

    # Reset Filter
    assert search.reset_filter()

    search.load_and_apply_filter(
        test_filter_save_and_cancel_load_with_user_input.filter_name,
        fill_callback={"COUNT": 0},
        cancel_on_user_filling=True
    )
    assert_no_cfme_exception()


def test_quick_search_without_filter(request, single_provider):
    assert_no_cfme_exception()
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(search.ensure_normal_search_empty)
    # Filter this host only
    search.normal_search(fauxfactory.gen_alphanumeric())
    assert_no_cfme_exception()


def test_quick_search_with_filter(request, single_provider):
    search.fill_and_apply_filter("fill_count(Infrastructure Provider.VMs, >=, 0)")
    assert_no_cfme_exception()
    # Make sure that we empty the regular search field after the test
    request.addfinalizer(search.ensure_normal_search_empty)
    # Filter this host only
    search.normal_search(fauxfactory.gen_alphanumeric())
    assert_no_cfme_exception()


def test_can_delete_filter(single_provider):
    filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(filter_name))
    assert search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)
    assert_no_cfme_exception()
    search.reset_filter()
    assert_no_cfme_exception()
    search.load_filter(filter_name)
    assert_no_cfme_exception()
    if not search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    assert_no_cfme_exception()


@pytest.mark.meta(blockers=[1097150, 1320244])
def test_delete_button_should_appear_after_save(single_provider, rails_delete_filter):
    """Delete button appears only after load, not after save"""
    # bind filter_name to the function for fixture cleanup
    test_delete_button_should_appear_after_save.filter_name = fauxfactory.gen_alphanumeric()
    search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)",
                       test_delete_button_should_appear_after_save.filter_name)

    if not search.delete_filter():  # Returns False if the button is not present
        pytest.fail("Could not delete filter right after saving!")


@pytest.mark.meta(blockers=[1097150, 1320244])
def test_cannot_delete_more_than_once(single_provider):
    """When Delete button appars, it does not want to go away"""
    filter_name = fauxfactory.gen_alphanumeric()
    assert search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)

    assert search.load_filter(filter_name)  # circumvent the thing happening in previous test
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
