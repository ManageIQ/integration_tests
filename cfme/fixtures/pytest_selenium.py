"""Provides a number of useful functions for integrating with selenium.

The aim is that no direct calls to selenium be made at all.
One reason for this it to ensure that all function calls to selenium wait for the ajax
response which is needed in CFME.

Members of this module are available in the the pytest.sel namespace, e.g.::

    pytest.sel.click(locator)

:var ajax_wait_js: A Javascript function for ajax wait checking
"""
from time import sleep, time
from collections import Iterable
import json

from pkg_resources import parse_version
from selenium.common.exceptions import \
    (ErrorInResponseException, InvalidSwitchToTargetException, NoSuchAttributeException,
     NoSuchElementException, NoAlertPresentException, UnexpectedAlertPresentException,
     InvalidElementStateException, MoveTargetOutOfBoundsException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from multimethods import singledispatch, multidispatch

import pytest
from cfme import exceptions
from utils import conf, lazycache
from utils.browser import browser, ensure_browser_open
from utils.log import logger
from utils.ssh import SSHClient


class Version(object):
    """
    A lazycached object which simply returns the appliance version.
    """
    @lazycache
    def version(self):
        """ A lazy cached method to return the appliance version. """
        return SSHClient().get_version()

ver = Version()


def ver_pick(v_dict):
    """
    Collapses an ambiguous series of objects bound to specific versions
    by interrogating the CFME Version and returning the correct item.
    """
    version = parse_version(ver.version)
    prev = None
    for ver_test in sorted([(parse_version(key), key) for key in v_dict.keys()]):
        if version >= ver_test[0]:
            prev = ver_test[1]
        else:
            break
    logger.debug(" Collapsing Singularity Cap'n, returning: {}".format(v_dict[prev]))
    return v_dict[prev]


class ByValue(object):
    def __init__(self, value):
        self.value = value


class ByText(object):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return str(self.text)


@singledispatch
def elements(o, root=None):
    """
    Convert object o to list of matching WebElements. Can be extended by registering the type of o
    to this function.

    Args:
        o: An object to be converted to a matching web element, eg str, WebElement, tuple.

    Returns: A list of WebElement objects
    """
    if hasattr(o, "locate"):
        return elements(o.locate(), root=root)
    elif callable(o):
        return elements(o(), root=root)
    else:
        raise TypeError("Unprocessable type for elements() -> {}".format(str(type(o))))
    # If it doesn't implement locate() or __call__(), we're in trouble so
    # let the error bubble up.


@elements.method(basestring)
def _s(s, **kwargs):
    """Assume string is an xpath locator.

    If the root element is actually multiple elements, then the locator is resolved for each
    of root nodes.

    Result: Flat list of elements
    """
    return elements((By.XPATH, s), **kwargs)


@elements.method(WebElement)
def _w(webelement, **kwargs):
    """Return a 1-item list of webelements

    If the root element is actually multiple elements, then the locator is resolved for each
    of root nodes.

    Result: Flat list of elements
    """
    # accept **kwargs to deal with root if it's passed by singledispatch
    return [webelement]


@elements.method(tuple)
def _t(t, root=None):
    """Assume tuple is a 2-item tuple like (By.ID, 'myid').

    Handles the case when root= locator resolves to multiple elements. In that case all of them
    are processed and all results are put in the same list."""
    result = []
    for root_element in (elements(root) if root is not None else [browser()]):
        result += root_element.find_elements(*t)
    return result


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
    t = time()
    return WebDriverWait(browser(), 120.0).until(f, msg) and time() - t


def _something_in_flight(s):
    blockers = ["blocker_div", "notification"]
    in_flt = s.execute_script(ajax_wait_js)
    if in_flt != 0:
        return True
    for blocker in blockers:
        if is_displayed((By.ID, blocker)):
            return True
    return False


def wait_for_ajax():
    """
    Waits unti lall ajax timers are complete, in other words, waits until there are no
    more pending ajax requests, page load should be finished completely.
    """
    return wait_until(lambda *a, **k: not _something_in_flight(*a, **k), "Ajax wait timed out")


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


def wait_for_element(*locs, **kwargs):
    """
    Wrapper around wait_until, specific to an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
    Keywords:
        all_elements: Whether to wait not for one, but all elements (Default False)
    """
    #wait_until(lambda s: is_displayed(loc), "Element '{}' did not appear as expected.".format(loc))
    filt = all if kwargs.get("all_elements", False) else any
    msg = "All" if kwargs.get("all_elements", False) else "Any"
    wait_until(
        lambda s: filt([is_displayed(loc) for loc in locs]),
        "{} of the elements '{}' did not appear as expected.".format(msg, str(locs))
    )


def on_cfme_page():
    """Check whether we are on a CFME page and not another or blank page"""
    return (is_displayed("//div[@id='page_header_div']//div[contains(@class, 'brand')]")
        and is_displayed("//div[@id='footer']")) or is_displayed("//ul[@class='login_buttons']")


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
        True if the alert was handled, False if exceptions were
        squashed, None if there was no alert.

    No exceptions will be raised if ``squash`` is True.

    Raises:
        utils.wait.TimedOutError: If the alert popup does not appear
        selenium.common.exceptions.NoAlertPresentException: If no alert is present when accepting
            or dismissing the alert.

    """

    # throws timeout exception if not found
    try:
        if wait:
            WebDriverWait(browser(), wait).until(expected_conditions.alert_is_present())
        popup = browser().switch_to_alert()
        answer = 'cancel' if cancel else 'ok'
        logger.info('Handling popup "%s", clicking %s' % (popup.text, answer))
        popup.dismiss() if cancel else popup.accept()
        wait_for_ajax()
        return True
    except NoAlertPresentException:
        return None
    except:
        if squash:
            return False
        else:
            raise


def click(loc, wait_ajax=True):
    """
    Clicks on an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        wait_ajax: Whether to wait for ajax call to finish. Default True but sometimes it's
            handy to not do that. (some toolbar clicks)
    """
    move_to_element(loc).click()
    if wait_ajax:
        wait_for_ajax()


def move_to_element(loc, **kwargs):
    """
    Moves to an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
    Returns: It passes `loc` through to make it possible to use in case we want to immediately use
        the element that it is being moved to.
    """
    brand = "//div[@id='page_header_div']//div[contains(@class, 'brand')]"
    wait_for_ajax()
    el = element(loc, **kwargs)
    try:
        ActionChains(browser()).move_to_element(el).perform()
    except MoveTargetOutOfBoundsException:
        # ff workaround
        browser().execute_script("arguments[0].scrollIntoView();", el)
        if elements(brand) and not is_displayed(brand):
            # If it does it badly that it moves whole page, this moves it back
            try:
                browser().execute_script("arguments[0].scrollIntoView();", element(brand))
            except MoveTargetOutOfBoundsException:
                pass
    return el


def text(loc):
    """
    Returns the text of an element.

    Args:
        loc: A locator, expects eithera  string, WebElement, tuple.

    Returns: A string containing the text of the element.
    """
    return element(loc).text


def value(loc):
    """
    Returns the value of an input element.

    Args:
        loc: A locator, expects eithera  string, WebElement, tuple.

    Returns: A string containing the value of the input element.
    """
    return get_attribute(loc, 'value')


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
        move_to_element(loc).send_keys(text)
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
        el = move_to_element(loc)
        if el.is_selected() is not set_to:
            logger.debug("Setting checkbox %s to %s" % (str(loc), str(set_to)))
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


def multi_check(locators):
    """ Mass-check and uncheck for checkboxes.

    Args:
        locators: :py:class:`dict` or :py:class:`list` or whatever iterable of tuples.
            Key is the locator, value bool with check status.
    """
    for locator, checked in dict(locators).iteritems():
        checkbox(locator, checked)


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
    def f(_):
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
    def f(_):
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


def base_url():
    """
    Returns the base url.

    Returns: `base_url` from env config yaml
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


def force_navigate(page_name, _tries=0, *args, **kwargs):
    """force_navigate(page_name)

    Given a page name, attempt to navigate to that page no matter what breaks.

    Args:
        page_name: Name a page from the current :py:data:`ui_navigate.nav_tree` tree to navigate to.

    """
    if _tries >= 2:
        # Need at least three tries:
        # 1: login_admin handles an alert or CannotContinueWithNavigation appears.
        # 2: Everything should work. If not, NavigationError.
        raise exceptions.NavigationError(page_name)

    _tries += 1

    logger.debug('force_navigate to %s, try %d' % (page_name, _tries))
    # circular import prevention: cfme.login uses functions in this module
    from cfme import login
    # Import the top-level nav menus for convenience
    from cfme.web_ui import menu

    # browser fixture should do this, but it's needed for subsequent calls
    ensure_browser_open()

    # Clear any running "spinnies"
    try:
        browser().execute_script('miqSparkleOff();')
    except:
        # miqSparkleOff undefined, so it's definitely off.
        pass

    # Set this to True in the handlers below to trigger a browser restart
    recycle = False

    try:
        # What we'd like to happen...
        login.login_admin()
        logger.info('Navigating to %s' % page_name)
        menu.nav.go_to(page_name, *args, **kwargs)
    except (KeyboardInterrupt, ValueError):
        # KeyboardInterrupt: Don't block this while navigating
        # ValueError: ui_navigate.go_to can't handle this page, give up
        raise
    except UnexpectedAlertPresentException:
        if _tries == 1:
            # There was an alert, accept it and try again
            handle_alert(wait=0)
            force_navigate(page_name, _tries, *args, **kwargs)
        else:
            # There was still an alert when we tried again, shoot the browser in the head
            logger.debug('Unxpected alert, recycling browser')
            recycle = True
    except (ErrorInResponseException, InvalidSwitchToTargetException):
        # Unable to switch to the browser at all, need to recycle
        logger.info('Invalid browser state, recycling browser')
        recycle = True
    except exceptions.CannotContinueWithNavigation as e:
        # The some of the navigation steps cannot succeed
        logger.info('Cannot continue with navigation due to: %s; Recycling browser' % str(e))
        recycle = True
    except (NoSuchElementException, InvalidElementStateException):
        from cfme.web_ui import cfme_exception as cfme_exc  # To prevent circular imports
        # If the page is blocked, then recycle...
        if is_displayed("//div[@id='blocker_div']"):
            logger.warning("Page was blocked with blocker div, recycling.")
            recycle = True
        elif cfme_exc.is_cfme_exception():
            logger.exception("CFME Exception before force_navigate started!: `{}`".format(
                cfme_exc.cfme_exception_text()
            ))
            recycle = True
        elif is_displayed("//body/div[@class='dialog' and ./h1 and ./p]"):
            # Rails exception detection
            logger.exception("Rails exception before force_navigate started!: {}:{} at {}".format(
                text("//body/div[@class='dialog']/h1").encode("utf-8"),
                text("//body/div[@class='dialog']/p").encode("utf-8"),
                current_url()
            ))
            recycle = True
        else:
            logger.error("Could not determine the reason for failing the navigation. Reraising.")
            raise

    if recycle:
        browser().quit()
        logger.debug('browser killed on try %d' % _tries)
        # If given a "start" nav destination, it won't be valid after quitting the browser
        kwargs.pop("start", None)
        force_navigate(page_name, _tries, *args, **kwargs)


def detect_observed_field(loc):
    """Detect observed fields; sleep if needed

    Used after filling most form fields, this function will inspect the filled field for
    one of the known CFME observed field attribues, and if found, sleep long enough for the observed
    field's AJAX request to go out, and then block until no AJAX requests are in flight.

    Observed fields occasionally declare their own wait interval before firing their AJAX request.
    If found, that interval will be used instead of the default.

    """
    if is_displayed(loc):
        el = element(loc)
    else:
        # Element not visible, sort out
        return

    # Default wait period, based on the default UI wait (700ms)
    # plus a little padding to let the AJAX fire before we wait_for_ajax
    default_wait = .8
    # Known observed field attributes
    observed_field_markers = (
        'data-miq_observe',
        'data-miq_observe_date',
        'data-miq_observe_checkbox',
    )
    for attr in observed_field_markers:
        try:
            observed_field_attr = el.get_attribute(attr)
            break
        except NoSuchAttributeException:
            pass
    else:
        # Failed to detect an observed text field, short out
        return

    try:
        attr_dict = json.loads(observed_field_attr)
        interval = float(attr_dict.get('interval', default_wait))
        # Pad the detected interval, as with default_wait
        interval += .1
    except (TypeError, ValueError):
        # ValueError and TypeError happens if the attribute value couldn't be decoded as JSON
        # ValueError also happens if interval couldn't be coerced to float
        # In either case, we've detected an observed text field and should wait
        interval = default_wait

    logger.debug('  Observed field detected, pausing %.1f seconds' % interval)
    sleep(interval)
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
        el = move_to_element(loc)
        el.clear()
        send_keys(el, text)


def make_it_select(o):
    """Make sure the object is select"""
    if isinstance(o, Select):
        move_to_element(o._el)
        return o
    else:
        return Select(move_to_element(o))


@multidispatch
def select(loc, o):
    raise NotImplementedError('Unable to select {} in this type: {}'.format(o, loc))


@select.method((object, ByValue))
def _select_tuple(loc, val):
    select_by_value(make_it_select(loc), val.value)


@select.method((object, basestring))
@select.method((object, ByText))
def _select_str(loc, s):
    select_by_text(make_it_select(loc), str(s))


@select.method((object, Iterable))
def _select_iter(loc, items):
    for item in items:
        select(loc, item)


def select_by_text(select_element, text):
    """
    Works on a select element and selects an option by the visible text.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The select element option's visible text.
    """
    if text is not None:
        select_element.select_by_visible_text(text)
        wait_for_ajax()


def select_by_value(select_element, value):
    """
    Works on a select element and selects an option by the value attribute.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        value: The select element's option value.
    """
    if value is not None:
        select_element.select_by_value(value)
        wait_for_ajax()


def deselect_by_text(select_element, text):
    """
    Works on a select element and deselects an option by the visible text.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The select element option's visible text.
    """
    if text is not None:
        select_element.deselect_by_visible_text(text)
        wait_for_ajax()


def deselect_by_value(select_element, value):
    """
    Works on a select element and deselects an option by the value attribute.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        value: The select element's option value.
    """
    if value is not None:
        select_element.deselect_by_value(value)
        wait_for_ajax()


@multidispatch
def deselect(loc, o):
    raise NotImplementedError('Unable to select {} in this type: {}'.format(o, loc))


@deselect.method((object, ByValue))
def _deselect_val(loc, val):
    deselect_by_value(make_it_select(loc), val.value)


@deselect.method((object, basestring))
@deselect.method((object, ByText))
def _deselect_text(loc, s):
    deselect_by_text(make_it_select(loc), str(s))


@deselect.method((object, Iterable))
def _deselect_iter(loc, items):
    for item in items:
        deselect(loc, item)
