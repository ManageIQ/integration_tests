# -*- coding: utf-8 -*-
"""This testing module tests the behaviour of the view.search box in the Provider section

It does not check for filtering results so far."""
import fauxfactory
import pytest
from selenium.common.exceptions import NoSuchElementException

from cfme.infrastructure.provider import InfraProvider
from fixtures.pytest_store import store
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.web_ui.cfme_exception import is_cfme_exception, cfme_exception_text


pytestmark = [
    pytest.mark.usefixtures("setup_cleanup_search", "infra_provider"), pytest.mark.tier(3)]


@pytest.yield_fixture(scope="function")
def setup_cleanup_search():
    """Navigate to InfraProvider, clear search on setup and teardown"""
    view = navigate_to(InfraProvider, 'All')
    view.search.remove_search_filters()
    yield
    # cleanup after test
    view.search.remove_search_filters()


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


def test_can_do_advanced_search():
    view = navigate_to(InfraProvider, 'All')
    assert view.search.is_advanced_search_possible, "Cannot do advanced view.search here!"


@pytest.mark.requires("test_can_do_advanced_search")
def test_can_open_advanced_search():
    view = navigate_to(InfraProvider, 'All')
    view.search.open_advanced_search()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_without_user_input():
    # Set up the filter
    view = navigate_to(InfraProvider, 'All')
    view.search.advanced_search(
        "fill_count(Infrastructure Provider.VMs, >=, 0)")
    view.flash.assert_no_error()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_with_user_input():
    # Set up the filter
    view = navigate_to(InfraProvider, 'All')
    logger.debug('DEBUG: test_with_user_input: fill and apply')
    view.search.advanced_search(
        "fill_count(Infrastructure Provider.VMs, >=)", {'COUNT': 0})
    view.flash.assert_no_error()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_with_user_input_and_cancellation():
    # Set up the filter
    view = navigate_to(InfraProvider, 'All')
    view.search.advanced_search(
        "fill_count(Infrastructure Provider.VMs, >=)", {"COUNT": 0}, True
    )
    view.flash.assert_no_error()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_cancel(rails_delete_filter):
    # bind filter_name to the function for fixture cleanup
    view = navigate_to(InfraProvider, 'All')
    test_filter_save_cancel.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(test_filter_save_cancel.filter_name))

    # Try save filter
    assert view.search.save_filter("fill_count(Infrastructure Provider.VMs, >)",
                                   test_filter_save_cancel.filter_name, cancel=True)
    view.flash.assert_no_error()

    assert view.search.reset_filter()
    # Exception depends on system state - Load button will be disabled if there are no saved filters
    with pytest.raises(NoSuchElementException):
        view.search.load_filter(saved_filter=test_filter_save_cancel.filter_name)


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_load(rails_delete_filter):
    # bind filter_name to the function for fixture cleanup
    view = navigate_to(InfraProvider, 'All')
    test_filter_save_and_load.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(test_filter_save_and_load.filter_name))

    # Save filter
    assert view.search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)",
                                   test_filter_save_and_load.filter_name)
    view.flash.assert_no_error()

    # Reset filter
    assert view.search.reset_filter()

    # Load filter
    assert view.search.load_filter(test_filter_save_and_load.filter_name)
    view.flash.assert_no_error()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_cancel_load(rails_delete_filter):
    # bind filter_name to the function for fixture cleanup
    test_filter_save_and_cancel_load.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(test_filter_save_and_cancel_load.filter_name))
    view = navigate_to(InfraProvider, 'All')
    # Save filter
    assert view.search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)",
                                   test_filter_save_and_cancel_load.filter_name)
    view.flash.assert_no_error()

    # Reset Filter
    assert view.search.reset_filter()

    # Load and cancel
    assert view.search.load_filter(test_filter_save_and_cancel_load.filter_name, cancel=True)
    view.flash.assert_no_error()


@pytest.mark.requires("test_can_open_advanced_search")
def test_filter_save_and_cancel_load_with_user_input(rails_delete_filter):
    # bind filter_name to the function for fixture cleanup
    test_filter_save_and_cancel_load_with_user_input.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(
        test_filter_save_and_cancel_load_with_user_input.filter_name))
    view = navigate_to(InfraProvider, 'All')
    # Save filter
    assert view.search.save_filter("fill_count(Infrastructure Provider.VMs, >)",
                                   test_filter_save_and_cancel_load_with_user_input.filter_name)
    view.flash.assert_no_error()

    # Reset Filter
    assert view.search.reset_filter()

    view.search.load_filter(
        test_filter_save_and_cancel_load_with_user_input.filter_name,
        fill_callback={"COUNT": 0},
        cancel_on_user_filling=True,
        apply=True
    )
    view.flash.assert_no_error()


def test_quick_search_without_filter(request):
    view = navigate_to(InfraProvider, 'All')
    # Make sure that we empty the regular view.search field after the test
    request.addfinalizer(view.search.remove_search_filters)
    # Filter this host only
    view.search.simple_search(fauxfactory.gen_alphanumeric())
    view.flash.assert_no_error()


def test_quick_search_with_filter(request):
    view = navigate_to(InfraProvider, 'All')
    view.search.advanced_search(
        "fill_count(Infrastructure Provider.VMs, >=, 0)")
    view.flash.assert_no_error()
    # Make sure that we empty the regular view.search field after the test
    request.addfinalizer(view.search.remove_search_filters)
    # Filter this host only
    view.search.simple_search(fauxfactory.gen_alphanumeric())
    view.flash.assert_no_error()


def test_can_delete_filter():
    view = navigate_to(InfraProvider, 'All')
    filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(filter_name))
    assert view.search.save_filter(
        "fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)
    view.flash.assert_no_error()
    view.search.reset_filter()
    view.flash.assert_no_error()
    view.search.load_filter(filter_name)
    view.flash.assert_no_error()
    if not view.search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    view.flash.assert_no_error()


def test_delete_button_should_appear_after_save(rails_delete_filter):
    """Delete button appears only after load, not after save"""
    # bind filter_name to the function for fixture cleanup
    view = navigate_to(InfraProvider, 'All')
    test_delete_button_should_appear_after_save.filter_name = fauxfactory.gen_alphanumeric()
    view.search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)",
                            test_delete_button_should_appear_after_save.filter_name)

    if not view.search.delete_filter():  # Returns False if the button is not present
        pytest.fail("Could not delete filter right after saving!")


def test_cannot_delete_more_than_once():
    """When Delete button appars, it does not want to go away"""
    view = navigate_to(InfraProvider, 'All')
    filter_name = fauxfactory.gen_alphanumeric()
    assert view.search.save_filter("fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)

    assert view.search.load_filter(filter_name)  # circumvent the thing happening in previous test
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
