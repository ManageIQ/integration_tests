"""This testing module tests the behaviour of the search box in the Provider section

It does not check for filtering results so far."""
import fauxfactory
import pytest
from selenium.common.exceptions import NoSuchElementException

from cfme import test_requirements
from cfme.fixtures.pytest_store import store
from cfme.infrastructure.provider import InfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.usefixtures("infra_provider"), pytest.mark.tier(3), test_requirements.filtering]


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
def advanced_search_view():
    view = navigate_to(InfraProvider, 'All')
    assert view.entities.search.is_advanced_search_possible, (
        "Cannot do advanced search here!")
    yield view
    view.entities.search.remove_search_filters()


def test_can_open_provider_advanced_search(advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    advanced_search_view.entities.search.open_advanced_search()


def test_provider_filter_without_user_input(advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # Set up the filter
    advanced_search_view.entities.search.advanced_search(
        "fill_count(Infrastructure Provider.VMs, >=, 0)")
    advanced_search_view.flash.assert_no_error()


def test_provider_filter_with_user_input(advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # Set up the filter
    logger.debug('DEBUG: test_with_user_input: fill and apply')
    advanced_search_view.entities.search.advanced_search(
        "fill_count(Infrastructure Provider.VMs, >=)", {'COUNT': 0})
    advanced_search_view.flash.assert_no_error()


def test_provider_filter_with_user_input_and_cancellation(advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # Set up the filtergit
    advanced_search_view.entities.search.advanced_search(
        "fill_count(Infrastructure Provider.VMs, >=)", {"COUNT": 0}, True
    )
    advanced_search_view.flash.assert_no_error()


def test_provider_filter_save_cancel(rails_delete_filter, advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # bind filter_name to the function for fixture cleanup
    test_provider_filter_save_cancel.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(test_provider_filter_save_cancel.filter_name))

    # Try save filter
    assert advanced_search_view.entities.search.save_filter(
        "fill_count(Infrastructure Provider.VMs, >)",
        test_provider_filter_save_cancel.filter_name, cancel=True)
    advanced_search_view.flash.assert_no_error()

    assert advanced_search_view.entities.search.reset_filter()
    # Exception depends on system state - Load button will be disabled if there are no saved filters
    with pytest.raises(NoSuchElementException):
        advanced_search_view.entities.search.load_filter(
            saved_filter=test_provider_filter_save_cancel.filter_name)


def test_provider_filter_save_and_load(rails_delete_filter, advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # bind filter_name to the function for fixture cleanup
    test_provider_filter_save_and_load.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(test_provider_filter_save_and_load.filter_name))

    # Save filter
    assert advanced_search_view.entities.search.save_filter(
        "fill_count(Infrastructure Provider.VMs, >, 0)",
        test_provider_filter_save_and_load.filter_name)
    advanced_search_view.flash.assert_no_error()

    # Reset filter
    assert advanced_search_view.entities.search.reset_filter()

    # Load filter
    assert advanced_search_view.entities.search.load_filter(
        test_provider_filter_save_and_load.filter_name
    )
    advanced_search_view.flash.assert_no_error()


def test_provider_filter_save_and_cancel_load(rails_delete_filter, advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # bind filter_name to the function for fixture cleanup
    test_provider_filter_save_and_cancel_load.filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(
        test_provider_filter_save_and_cancel_load.filter_name)
    )
    # Save filter
    assert advanced_search_view.entities.search.save_filter(
        "fill_count(Infrastructure Provider.VMs, >, 0)",
        test_provider_filter_save_and_cancel_load.filter_name)
    advanced_search_view.flash.assert_no_error()

    # Reset Filter
    assert advanced_search_view.entities.search.reset_filter()

    # Load and cancel
    assert advanced_search_view.entities.search.load_filter(
        test_provider_filter_save_and_cancel_load.filter_name, cancel=True)
    advanced_search_view.flash.assert_no_error()


def test_provider_filter_save_and_cancel_load_with_user_input(
        rails_delete_filter, advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # bind filter_name to the function for fixture cleanup
    test_provider_filter_save_and_cancel_load_with_user_input.filter_name = \
        fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(
        test_provider_filter_save_and_cancel_load_with_user_input.filter_name))
    # Save filter
    assert advanced_search_view.entities.search.save_filter(
        "fill_count(Infrastructure Provider.VMs, >)",
        test_provider_filter_save_and_cancel_load_with_user_input.filter_name)
    advanced_search_view.flash.assert_no_error()

    # Reset Filter
    assert advanced_search_view.entities.search.reset_filter()
    advanced_search_view.entities.search.load_filter(
        test_provider_filter_save_and_cancel_load_with_user_input.filter_name,
        fill_callback={"COUNT": 0},
        cancel_on_user_filling=True,
        apply_filter=True
    )
    advanced_search_view.flash.assert_no_error()


def test_quick_search_without_provider_filter(request):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    view = navigate_to(InfraProvider, 'All')
    # Make sure that we empty the regular view.entities.search field after the test
    request.addfinalizer(view.entities.search.clear_simple_search)
    # Filter this host only
    view.entities.search.simple_search(fauxfactory.gen_alphanumeric())
    view.flash.assert_no_error()


def test_quick_search_with_provider_filter(request):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    view = navigate_to(InfraProvider, 'All')
    view.entities.search.advanced_search(
        "fill_count(Infrastructure Provider.VMs, >=, 0)")
    view.flash.assert_no_error()
    # Make sure that we empty the regular view.entities.search field after the test
    request.addfinalizer(view.entities.search.remove_search_filters)
    # Filter this host only
    view.entities.search.simple_search(fauxfactory.gen_alphanumeric())
    view.flash.assert_no_error()


def test_can_delete_provider_filter(advanced_search_view):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    logger.debug('Set filter_name to: {}'.format(filter_name))
    assert advanced_search_view.entities.search.save_filter(
        "fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)
    advanced_search_view.flash.assert_no_error()
    advanced_search_view.entities.search.reset_filter()
    advanced_search_view.flash.assert_no_error()
    advanced_search_view.entities.search.load_filter(filter_name)
    advanced_search_view.flash.assert_no_error()
    if not advanced_search_view.entities.search.delete_filter():
        raise pytest.fail("Cannot delete filter! Probably the delete button is not present!")
    advanced_search_view.flash.assert_no_error()


def test_delete_button_should_appear_after_save_provider(rails_delete_filter, advanced_search_view):
    """Delete button appears only after load, not after save

    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    # bind filter_name to the function for fixture cleanup
    test_delete_button_should_appear_after_save_provider.filter_name = \
        fauxfactory.gen_alphanumeric()
    advanced_search_view.entities.search.save_filter(
        "fill_count(Infrastructure Provider.VMs, >, 0)",
        test_delete_button_should_appear_after_save_provider.filter_name)

    if not advanced_search_view.entities.search.delete_filter():
        # Returns False if the button is not present
        pytest.fail("Could not delete filter right after saving!")


def test_cannot_delete_provider_filter_more_than_once(advanced_search_view):
    """When Delete button appars, it does not want to go away

    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    assert advanced_search_view.entities.search.save_filter(
        "fill_count(Infrastructure Provider.VMs, >, 0)", filter_name)
    # circumvent the thing happening in previous test
    assert advanced_search_view.entities.search.load_filter(filter_name)
    # Delete once
    if not advanced_search_view.entities.search.delete_filter():
        pytest.fail("Could not delete the filter even first time!")
        advanced_search_view.flash.assert_no_error()
    # Try it second time
    assert not advanced_search_view.entities.search.delete_filter(), 'Delete twice accepted!'
