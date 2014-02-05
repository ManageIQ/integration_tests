"""Provides a number of useful functions for integrating with selenium.

The aim is that no direct calls to selenium be made at all.
One reason for this it to ensure that all function calls to selenium wait for the ajax
response which is needed in CFME.

Members of this module are available in the the pytest.sel namespace, e.g.::

    pytest.sel.click(locator)

:var ajax_wait_js: A Javascript function for ajax wait checking
"""
import time

import ui_navigate
from selenium.common.exceptions import NoSuchElementException, UnexpectedAlertPresentException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from singledispatch import singledispatch

import pytest
from cfme import exceptions
from utils import conf
from utils.browser import browser, ensure_browser_open
from utils.log import logger

VALUE = 'val'
TEXT = 'txt'


def pytest_namespace():
    # Return the contents of this file as the 'sel' namespace in pytest.
    return {'sel': globals()}


@singledispatch
def elements(o, root=None):
    """
    Convert object o to list of matching WebElements. Can be extended by registering the type of o
    to this function.

    Args:
        o: An object to be converted to a matching web element, eg str, WebElement, tuple.

    Returns: A list of WebElement objects
    """
    return elements(o.locate(), root=root)  # if object implements locate(), try to get elements
    # from that locator.  If it doesn't implement locate(), we're in trouble so
    # let the error bubble up.


@elements.register(basestring)
def _s(s, root=None):
    """Assume string is an xpath locator"""
    parent = root or browser()
    return parent.find_elements_by_xpath(s)


@elements.register(WebElement)
def _w(webelement):
    """Return a 1-item list of webelements"""
    return [webelement]


@elements.register(tuple)
def _t(t, root=None):
    """Assume tuple is a 2-item tuple like (By.ID, 'myid')"""
    parent = root or browser()
    return parent.find_elements(*t)


def element(o, **kwargs):
    """
    Convert o to a single matching WebElement.

    Args:
        o: An object to be converted to a matching web element, expected string, WebElement, tuple.

    Returns: A WebElement object

    Raises:
        NoSuchElementException: When element is not found on page
    """
    matches = elements(o, **kwargs)
    if not matches:
        raise NoSuchElementException("Element {} not found on page.".format(str(o)))
    return matches[0]


def wait_until(f, msg="Webdriver wait timed out"):
    """
    Wrapper around WebDriverWait from selenium
    """
    WebDriverWait(browser(), 120.0).until(f, msg)


def _nothing_in_flight(s):
    in_flt = s.execute_script(ajax_wait_js)
    return in_flt == 0


def wait_for_ajax():
    """
    Waits unti lall ajax timers are complete, in other words, waits until there are no
    more pending ajax requests, page load should be finished completely.
    """
    wait_until(_nothing_in_flight, "Ajax wait timed out")


def is_displayed(loc):
    """
    Checks if a particular locator is displayed

    Args:
        loc: A locator, expects either a  string, WebElement, tuple.

    Returns: ``True`` if element is displayed, ``False`` if not

    Raises:
        NoSuchElementException: If element is not found on page
    """
    try:
        return element(loc).is_displayed()
    except NoSuchElementException:
        return False


def wait_for_element(loc):
    """
    Wrapper around wait_until, specific to an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
    """
    wait_until(lambda s: is_displayed(loc), "Element '{}' did not appear as expected.".format(loc))


def handle_alert(cancel=False, wait=30.0, squash=False):
    """Handles an alert popup.

    Args:
        cancel: Whether or not to cancel the alert.
            Accepts the Alert (False) by default.
        wait: Time to wait for an alert to appear.
            Default 30 seconds, can be set to 0 to disable waiting.
        squash: Whether or not to squash errors during alert handling.
            Default False

    Returns:
        True if the alert was handled, False if exceptions were squashed.

    No exceptions will be raised if ``squash`` is True.

    Raises:
        utils.wait.TimedOutError: If the alert popup does not appear
        selenium.common.exceptions.NoAlertPresentException: If no alert is present when accepting
            or dismissing the alert.

    """

    # throws timeout exception if not found
    try:
        if wait:
            wait = WebDriverWait(browser(), 30.0)
            wait.until(expected_conditions.alert_is_present())
        popup = browser().switch_to_alert()
        answer = 'cancel' if cancel else 'ok'
        logger.info('Handling popup "%s", clicking %s' % (popup.text, answer))
        popup.dismiss() if cancel else popup.accept()
        return True
    except:
        if squash:
            return False
        else:
            raise


def click(loc):
    """
    Clicks on an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
    """
    ActionChains(browser()).move_to_element(element(loc)).click().perform()
    wait_for_ajax()


def move_to_element(loc):
    """
    Moves to an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
    """
    ActionChains(browser()).move_to_element(element(loc)).perform()


def text(loc):
    """
    Returns the text of an element.

    Args:
        loc: A locator, expects eithera  string, WebElement, tuple.

    Returns: A string containing the text of the element.
    """
    return element(loc).text


def tag(loc):
    """
    Returns the tag name of an element

    Args:
        loc: A locator, expects either a string, WebElement, tuple.

    Returns: A string containing the tag element's name.
    """
    return element(loc).tag_name


def get_attribute(loc, attr):
    """
    Returns the value of the HTML attribute of the given locator.

    Args:
        loc: A locator, expects eithera string, WebElement, tuple.
        attr: An attribute name.

    Returns: Text describing the attribute of the element.
    """
    return element(loc).get_attribute(attr)


def send_keys(loc, text):
    """
    Sends the supplied keys to an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The text to inject into the element.
    """
    if text is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).send_keys_to_element(el, text).perform()
        wait_for_ajax()


@singledispatch
def set_text(loc, text):
    """
    Clears the element and then sends the supplied keys.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The text to inject into the element.
    """
    if text is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        el.clear()
        el.send_keys(text)
        wait_for_ajax()


def select(loc, o):
    """
    Takes a locator and an object and selects using the correct method.

    If o is a string, then it is assumed the user wishes to select by visible text.
    If o is a tuple, then the first argument defines the type. Either ``TEXT`` or ``VALUE``.
    A choice of select method is then determined.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        o: An object, can be either a string or a tuple.
    """
    if isinstance(o, basestring):
        select_by_text(loc, o)
    else:
        vtype, value = o
        if vtype == TEXT:
            select_by_text(loc, value)
        if vtype == VALUE:
            select_by_value(loc, value)


def select_by_text(loc, text):
    """
    Works on a select element and selects an option by the visible text.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The select element option's visible text.
    """
    if text is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        Select(el).select_by_visible_text(text)
        wait_for_ajax()


def select_by_value(loc, value):
    """
    Works on a select element and selects an option by the value attribute.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        value: The select element's option value.
    """
    if value is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        Select(el).select_by_value(value)
        wait_for_ajax()


def deselect(loc, o):
    """
    Takes a locator and an object and deselects using the correct method.

    If o is a string, then it is assumed the user wishes to select by visible text.
    If o is a tuple, then the first argument defines the type. Either ``TEXT`` or ``VALUE``.
    A choice of select method is then determined.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        o: An object, can be either a string or a tuple.
    """
    if isinstance(o, basestring):
        deselect_by_text(loc, o)
    else:
        vtype, value = o
        if vtype == TEXT:
            deselect_by_text(loc, value)
        if vtype == VALUE:
            deselect_by_value(loc, value)


def deselect_by_text(loc, text):
    """
    Works on a select element and deselects an option by the visible text.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The select element option's visible text.
    """
    if text is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        Select(el).deselect_by_visible_text(text)
        wait_for_ajax()


def deselect_by_value(loc, value):
    """
    Works on a select element and deselects an option by the value attribute.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        value: The select element's option value.
    """
    if value is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        Select(el).deselect_by_value(value)
        wait_for_ajax()


def checkbox(loc, set_to=False):
    """
    Checks or unchecks a given checkbox

    Finds an element given by loc and checks it

    Args:
        loc: The locator of the element
        value: The value the checkbox should represent as a bool (or None to do nothing)

    Returns: None
    """
    if set_to is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        if el.is_selected() is not set_to:
            click(el)


def check(loc):
    """
    Convenience function to check a checkbox

    Args:
        loc: The locator of the element
    """
    checkbox(loc, True)


def uncheck(loc):
    """
    Convenience function to uncheck a checkbox

    Args:
        loc: The locator of the element
    """
    checkbox(loc, False)


def current_url():
    """
    Returns the current_url of the page

    Returns: A url.
    """
    return browser().current_url


def get(url):
    """
    Changes page to the spceified URL

    Args:
        url: URL to navigate to.
    """
    return browser().get(url)


def refresh():
    """
    Refreshes the current browser window.
    """
    browser().refresh()


def move_to_fn(*els):
    """
    Returns a function which successively moves through a series of elements.

    Args:
        els: An iterable of elements:
    Returns: The move function
    """
    def f():
        for el in els:
            move_to_element(el)
    return f


def click_fn(*els):
    """
    Returns a function which successively clicks on a series of elements.

    Args:
       els: An iterable of elements:
    Returns: The click function
    """
    def f():
        for el in els:
            click(el)
    return f


def first_from(*locs, **kwargs):
    """ Goes through locators and first valid element received is returned.

    Useful for things that could be located different way

    Args:
        *locs: Locators to pass through
        **kwargs: Keyword arguments to pass to element()
    Raises:
        NoSuchElementException: When none of the locator could find the element.
    Returns: :py:class:`WebElement`
    """
    assert len(locs) > 0, "You must provide at least one locator to look for!"
    for locator in locs:
        try:
            return element(locator, **kwargs)
        except NoSuchElementException:
            pass
    # To make nice error
    msg = locs[0] if len(locs) == 1 else ("%s or %s" % (", ".join(locs[:-1]), locs[-1]))
    raise NoSuchElementException("Could not find element with possible locators %s." % msg)

# Begin CFME specific stuff, should eventually factor
# out everything above into a lib


def baseurl():
    """
    Returns the baseurl.

    Returns: The baseurl.
    """
    return conf.env['base_url']


ajax_wait_js = """
var inflight = function() {
    return Array.prototype.slice.call(arguments,0).reduce(function (n, f) {
        try {flt = f() || 0;
             flt=(Math.abs(flt)+flt)/2; return flt + n;} catch (e) { return n }}, 0)};
return inflight(function() { return jQuery.active},
                function() { return Ajax.activeRequestCount},
                function() { return window.miqAjaxTimers},
                function() { if (document.readyState == "complete") { return 0 } else { return 1}});
"""


class ObservedText(object):
    """A class to represent an observed textbox in CFME.
    That means that as we type into this textbox, the js periodically
    checks if it's not been typed in in the last x seconds.  If not,
    an ajax call is made (presumably to validate the input).
    """

    def __init__(self, locator):
        self.locator = locator


@set_text.register(ObservedText)
def _sd_set_text_string(ot, text):
    """When setting text on an ObservedText, wait after typing
    until the timer expires and fires the ajax event.
    """
    if text is not None:
        el = element(ot)
        ActionChains(browser()).move_to_element(el).perform()
        el.clear()
        el.send_keys(text)
        time.sleep(0.8)
        wait_for_ajax()


@elements.register(ObservedText)
def _sd_elements_otext(ot):
    """The elements of an ObservedText is just the elements of
    its locator."""
    return elements(ot.locator)


def go_to(page_name):
    """go_to task mark, used to ensure tests start on the named page, logged in as Administrator.

    Args:
        page_name: Name a page from the current :py:data:`ui_navigate.nav_tree` tree to navigate to.

    Usage:
        @pytest.sel.go_to('page_name')
        def test_something_on_page_name():
            # ...

    """
    def go_to_wrapper(test_callable):
        # Optional, but cool. Marks a test with the page_name, so you can
        # py.test -k page_name
        test_callable = getattr(pytest.mark, page_name)(test_callable)
        # Use fixtureconf to mark the test with destination page_name
        test_callable = pytest.mark.fixtureconf(page_name=page_name)(test_callable)
        # Use the 'go_to' fixture, which looks for the page_name fixtureconf
        test_callable = pytest.mark.usefixtures('go_to_fixture')(test_callable)
        return test_callable
    return go_to_wrapper


@pytest.fixture
def go_to_fixture(fixtureconf, browser):
    """"Private" implementation of go_to in fixture form.

    Used by the :py:func:`go_to` decorator, this is the actual fixture that does
    the work set up by the go_to decorator. py.test fixtures themselves can't have
    underscores in their name, so we can't imply privacy with that convention.

    Don't use this fixture directly, use the go_to decorator instead.

    """
    page_name = fixtureconf['page_name']
    force_navigate(page_name)


def force_navigate(page_name, tries=0):
    """force_navigate(page_name)

    Given a page name, attempt to navigate to that page no matter what breaks.

    Args:
        page_name: Name a page from the current :py:data:`ui_navigate.nav_tree` tree to navigate to.

    """
    # circular import prevention: cfme.login uses functions in this module
    from cfme import login
    # Import the top-level nav menus for convenience
    from cfme.web_ui import menu  # NOQA

    if tries < 3:
        tries += 1
    else:
        # Need at least three tries:
        # 1: login_admin handles an alert or closes the browser due any error
        # 2: If login_admin handles an alert, go_to can still encounter an unexpected error
        # 3: Everything should work. If not, NavigationError.
        raise exceptions.NavigationError(page_name)

    # browser fixture should do this, but it's needed for subsequent calls
    ensure_browser_open()
    # Clear any running "spinnies"
    try:
        browser().execute_script('miqSparkleOff();')
    except:
        # miqSparkleOff undefined, so it's definitely off.
        pass

    try:
        # What we'd like to happen...
        login.login_admin()
        logger.info('Navigating to %s' % page_name)
        ui_navigate.go_to(page_name)
    except ValueError:
        # ui_navigate.go_to can't handle this page, raise
        raise
    except UnexpectedAlertPresentException:
        # There was an alert, accept it and try again
        handle_alert(wait=0)
        force_navigate(page_name, tries)
    except:
        # Anything else happened, nuke the browser and try again.
        browser().quit()
        logger.error('Browser failure during navigation, trying again.')
        force_navigate(page_name, tries)
