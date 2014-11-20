"""Provides a number of useful functions for integrating with selenium.

The aim is that no direct calls to selenium be made at all.
One reason for this it to ensure that all function calls to selenium wait for the ajax
response which is needed in CFME.

Members of this module are available in the the pytest.sel namespace, e.g.::

    pytest.sel.click(locator)

:var ajax_wait_js: A Javascript function for ajax wait checking
:var class_selector: Regular expression to detect simple CSS locators
"""

from time import sleep, time
from xml.sax.saxutils import quoteattr
from collections import Iterable
from textwrap import dedent
import json
import re
from selenium.common.exceptions import \
    (ErrorInResponseException, InvalidSwitchToTargetException, NoSuchAttributeException,
     NoSuchElementException, NoAlertPresentException, UnexpectedAlertPresentException,
     InvalidElementStateException, MoveTargetOutOfBoundsException, WebDriverException,
     StaleElementReferenceException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select as SeleniumSelect
from multimethods import singledispatch, multidispatch

import pytest
from cfme import exceptions, js
from fixtures.pytest_store import store
from utils import version
from utils.browser import browser, ensure_browser_open
from utils.log import logger
from utils.wait import wait_for
from utils.pretty import Pretty

from threading import local
_thread_local = local()

class_selector = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9]*)?(?:[#.][a-zA-Z0-9_-]+)+$")


class ByValue(Pretty):
    pretty_attrs = ['value']

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value


class ByText(Pretty):
    pretty_attrs = ['text']

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return str(self.text)

    def __eq__(self, other):
        return self.text == other.text


@singledispatch
def elements(o, **kwargs):
    """
    Convert object o to list of matching WebElements. Can be extended by registering the type of o
    to this function.

    Args:
        o: An object to be converted to a matching web element, eg str, WebElement, tuple.

    Returns: A list of WebElement objects
    """
    if hasattr(o, "locate"):
        return elements(o.locate(), **kwargs)
    elif callable(o):
        return elements(o(), **kwargs)
    else:
        raise TypeError("Unprocessable type for elements({}) -> class {} (kwargs: {})".format(
            str(repr(o)), o.__class__.__name__, str(repr(kwargs))
        ))
    # If it doesn't implement locate() or __call__(), we're in trouble so
    # let the error bubble up.


@elements.method(basestring)
def _s(s, **kwargs):
    """Detect string and process it into locator.

    If the string starts with # or ., it is considered as CSS selector.
    If the string is in format tag#id.class2 it is considered as CSS selector format too.
    No other forms of CSS selectors are supported (use tuples if you really want to)
    Otherwise it is assumed it is an XPATH selector.

    If the root element is actually multiple elements, then the locator is resolved for each
    of root nodes.

    Result: Flat list of elements
    """
    s = s.strip()
    css = class_selector.match(s)
    if css is not None:
        return elements((By.CSS_SELECTOR, css.group()), **kwargs)
    else:
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
        # 20140920 - dajo - hack to get around selenium e is null bs
        count = 0
        while count < 8:
            count += 1
            try:
                result += root_element.find_elements(*t)
                break
            except Exception as e:
                logger.info('Exception detected: ' + str(e))
                sleep(0.25)
                if count == 8:
                    result += root_element.find_elements(*t)
    return result


@elements.method(list)
@elements.method(set)
def _l(l, **kwargs):
    """If we pass an iterable (non-tuple), just find everything relevant from it by all locators."""
    found = reduce(lambda a, b: a + b, map(lambda loc: elements(loc, **kwargs), l))
    seen = set([])
    result = []
    # Multiple locators can find the same elements, so let's filter
    for item in found:
        if item in seen:
            continue
        result.append(item)
        seen.add(item)
    return result


@elements.method(dict)
def _d(l, **kwargs):
    """Resolve version-specific locators."""
    return elements(version.pick(l), **kwargs)


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


def in_flight():
    """Check remaining (running) ajax requests

    The element visibility check is complex because lightbox_div invokes visibility
    of spinner_div although it is not visible.

    Returns:
        Dictionary of js-related keys and booleans as its values, depending on status.
        The keys are: ``jquery, prototype, miq, spinner and document``.
        The values are: ``True`` if running, ``False`` otherwise.
    """
    try:
        return execute_script(js.in_flight)
    except:
        sleep(0.5)
        return execute_script(js.in_flight)


def wait_for_ajax():
    """
    Waits until all ajax timers are complete, in other words, waits until there are no
    more pending ajax requests, page load should be finished completely.

    Raises:
        TimedOutError: when ajax did not load in time
    """

    _thread_local.ajax_log_msg = ''

    def _nothing_in_flight():
        """Checks if there is no ajax in flight and also logs current status
        """
        prev_log_msg = _thread_local.ajax_log_msg

        running = in_flight()
        anything_in_flight = False
        anything_in_flight |= running["jquery"] > 0
        anything_in_flight |= running["prototype"] > 0
        anything_in_flight |= running["spinner"]
        anything_in_flight |= running["document"] != "complete"
        log_msg = ', '.join(["{}: {}".format(k, str(v)) for k, v in running.iteritems()])
        # Log the message only if it's different from the last one
        if prev_log_msg != log_msg:
            _thread_local.ajax_log_msg = log_msg
            logger.trace('Ajax running: {}'.format(log_msg))
        if (not anything_in_flight) and prev_log_msg:
            logger.trace('Ajax done')

        return not anything_in_flight

    wait_for(
        _nothing_in_flight,
        num_sec=30, delay=0.1, message="wait for ajax", quiet=True, silent_failure=True)


def is_displayed(loc, _deep=0):
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
    except StaleElementReferenceException:
        # It can happen sometimes that the change will happen between element lookup and visibility
        # check. Then StaleElementReferenceException happens. We give it two additional tries.
        # One regular. And one if something really bad happens. We don't check WebElements as it has
        # no point.
        if _deep >= 2 or isinstance(loc, WebElement):
            # Too deep, or WebElement, which has no effect in repeating
            raise
        else:
            # So try it again after a little bit of sleep
            sleep(0.05)
            return is_displayed(loc, _deep + 1)


def is_displayed_text(text):
    """
    Checks if a particular text is displayed

    Args:
        text: A string.

    Returns: A string containing the text
    """
    return is_displayed("//*[text()={}]".format(quoteattr(text)))


def wait_for_element(*locs, **kwargs):
    """
    Wrapper around wait_until, specific to an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
    Keywords:
        all_elements: Whether to wait not for one, but all elements (Default False)
    """
    # wait_until(lambda s: is_displayed(loc),"Element '{}' did not appear as expected.".format(loc))
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


def click(loc, wait_ajax=True, no_custom_handler=False):
    """
    Clicks on an element.

    If the element implements `_custom_click_handler` the control will be given to it. Then the
    handler decides what to do (eg. do not click under some circumstances).

    Args:
        loc: A locator, expects either a string, WebElement, tuple or an object implementing
            `_custom_click_handler` method.
        wait_ajax: Whether to wait for ajax call to finish. Default True but sometimes it's
            handy to not do that. (some toolbar clicks)
        no_custom_handler: To prevent recursion, the custom handler sets this to True.
    """
    if hasattr(loc, "_custom_click_handler") and not no_custom_handler:
        # Object can implement own modification of click behaviour
        return loc._custom_click_handler()

    # Move mouse cursor to element
    move_to_element(loc)
    # and then click on current mouse position
    ActionChains(browser()).click().perform()
    # -> using this approach, we don't check if we clicked a specific element
    if wait_ajax:
        wait_for_ajax()
    return True


def raw_click(loc, wait_ajax=True):
    """Does raw selenium's .click() call on element. Circumvents mouse move.

    Args:
        loc: Locator to click on.
        wait_ajax: Whether to wait for ajax.
    """
    element(loc).click()
    if wait_ajax:
        wait_for_ajax()


def double_click(loc, wait_ajax=True):
    """Double-clicks on an element.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        wait_ajax: Whether to wait for ajax call to finish. Default True but sometimes it's
            handy to not do that. (some toolbar clicks)
    """
    # Move mouse cursor to element
    move_to_element(loc)
    # and then click on current mouse position
    ActionChains(browser()).double_click().perform()
    # -> using this approach, we don't check if we clicked a specific element
    if wait_ajax:
        wait_for_ajax()
    return True


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
    move_to = ActionChains(browser()).move_to_element(el)
    try:
        move_to.perform()
    except MoveTargetOutOfBoundsException:
        # ff workaround
        execute_script("arguments[0].scrollIntoView();", el)
        if elements(brand) and not is_displayed(brand):
            # If it does it badly that it moves whole page, this moves it back
            try:
                execute_script("arguments[0].scrollIntoView();", element(brand))
            except MoveTargetOutOfBoundsException:
                pass
        try:
            move_to.perform()
        except MoveTargetOutOfBoundsException:  # This has become desperate now.
            raise exceptions.CannotScrollException(
                "Despite all the workarounds, scrolling to `{}` was unsuccessful.".format(loc))
    return el


def text(loc, **kwargs):
    """
    Returns the text of an element.

    Args:
        loc: A locator, expects eithera  string, WebElement, tuple.

    Returns: A string containing the text of the element.
    """
    return element(loc, **kwargs).text


def text_sane(loc, **kwargs):
    """Returns text decoded from UTF-8 and stripped

    Args:
        loc: A locator, expects eithera  string, WebElement, tuple.

    Returns: A string containing the text of the element, decoded and stripped.
    """
    return text(loc).encode("utf-8").strip()


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


def set_attribute(loc, attr, value):
    """Sets the attribute of an element.

    This is usually not done, that's why it is not implemented in selenium. But sometimes ...

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        attr: Attribute name.
        value: Value to set.
    """
    logger.info(
        "!!! ATTENTION! SETTING READ-ONLY ATTRIBUTE {} OF {} TO {}!!!".format(attr, loc, value))
    return execute_script(
        "arguments[0].setAttribute(arguments[1], arguments[2]);", element(loc), attr, value)


def unset_attribute(loc, attr):
    """Removes an attribute of an element.

    This is usually not done, that's why it is not implemented in selenium. But sometimes ...

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        attr: Attribute name.
    """
    logger.info("!!! ATTENTION! REMOVING READ-ONLY ATTRIBUTE {} OF {} TO {}!!!".format(attr, loc))
    return execute_script("arguments[0].removeAttribute(arguments[1]);", element(loc), attr)


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

    Returns: Previous state of the checkbox
    """
    if set_to is not None:
        el = move_to_element(loc)
        selected = el.is_selected()
        if selected is not set_to:
            logger.debug("Setting checkbox %s to %s" % (str(loc), str(set_to)))
            click(el)
        return selected


def check(loc):
    """
    Convenience function to check a checkbox

    Args:
        loc: The locator of the element
    """
    return checkbox(loc, True)


def uncheck(loc):
    """
    Convenience function to uncheck a checkbox

    Args:
        loc: The locator of the element
    """
    return checkbox(loc, False)


def multi_check(locators):
    """ Mass-check and uncheck for checkboxes.

    Args:
        locators: :py:class:`dict` or :py:class:`list` or whatever iterable of tuples.
            Key is the locator, value bool with check status.

    Returns: list of booleans indicating for each locator, whether any action was taken.

    """
    return [checkbox(locator, checked) for locator, checked in dict(locators).iteritems()]


def current_url():
    """
    Returns the current_url of the page

    Returns: A url.
    """
    return browser().current_url


def title():
    return browser().title


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
    return store.base_url


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
    if _tries > 2:
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
        execute_script('miqSparkleOff();')
    except:
        # miqSparkleOff undefined, so it's definitely off.
        pass

    # Set this to True in the handlers below to trigger a browser restart
    recycle = False

    # remember the current user, if any
    current_user = login.current_user()

    # Check if the page is blocked with blocker_div. If yes, let's headshot the browser right here
    if is_displayed("//div[@id='blocker_div']"):
        logger.warning("Page was blocked with blocker div on start of navigation, recycling.")
        browser().quit()
        kwargs.pop("start", None)
        force_navigate("dashboard")  # Start fresh

    try:
        # What we'd like to happen...
        if not current_user:  # default to admin user
            login.login_admin()
        else:  # we recycled and want to log back in
            login.login(current_user.username, current_user.password)
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
    except (NoSuchElementException, InvalidElementStateException, WebDriverException) as e:
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
        elif elements("//ul[@id='maintab']/li[@class='inactive']") and not\
                elements("//ul[@id='maintab']/li[@class='active']/ul/li"):
            # If upstream and is the bottom part of menu is not displayed
            logger.exception("Detected glitch from BZ#1112574. HEADSHOT!")
            recycle = True
        else:
            logger.error("Could not determine the reason for failing the navigation. " +
                " Reraising.  Exception: %s" % str(e))
            raise

    if recycle:
        browser().quit()  # login.current_user() will be retained for next login
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
    try:
        if is_displayed(loc):
            el = element(loc)
        else:
            # Element not visible, sort out
            return
    except StaleElementReferenceException:
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

    logger.trace('  Observed field detected, pausing %.1f seconds' % interval)
    sleep(interval)
    wait_for_ajax()


@singledispatch
def set_text(loc, text):
    """
    Clears the element and then sends the supplied keys.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The text to inject into the element.

    Returns:
        Any text that might have been in the textbox element already
    """
    if text is not None:
        el = move_to_element(loc)
        old_text = el.get_attribute('value')
        if text != old_text:
            el.clear()
            send_keys(el, text)
        return old_text


class Select(SeleniumSelect, Pretty):
    """ A proxy class for the real selenium Select() object.

    We differ in one important point, that we can instantiate the object
    without it being present on the page. The object is located at the beginning
    of each function call.

    Args:
        loc: A locator.

    Returns: A :py:class:`cfme.web_ui.Select` object.
    """

    pretty_attrs = ['_loc', 'is_multiple']

    def __init__(self, loc, multi=False):
        if isinstance(loc, Select):
            self._loc = loc._loc
        else:
            self._loc = loc
        self.is_multiple = multi

    @property
    def _el(self):
        return move_to_element(self)

    @property
    def all_selected_options(self):
        """Fast variant of the original all_selected_options.

        Selenium's all_selected_options iterates over ALL of the options, this directly returns
        only those that are selected.
        """
        return execute_script("return arguments[0].selectedOptions;", element(self))

    @property
    def first_selected_option(self):
        """Fast variant of the original first_selected_option.

        Uses all_selected_options, mimics selenium's exception behaviour.
        """
        try:
            return self.all_selected_options[0]
        except IndexError:
            raise NoSuchElementException("No options are selected")

    def deselect_all(self):
        """Fast variant of the original deselect_all.

        Uses all_selected_options, mimics selenium's exception behaviour.
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect all options of a multi-select")
        for opt in self.all_selected_options:
            raw_click(opt)

    def locate(self):
        return move_to_element(self._loc)

    def observer_wait(self):
        detect_observed_field(self._loc)

    def __str__(self):
        return "<%s.Select loc='%s'>" % (__name__, self._loc)


@multidispatch
def select(loc, o):
    raise NotImplementedError('Unable to select {} in this type: {}'.format(o, loc))


@select.method((object, ByValue))
def _select_tuple(loc, val):
    return select_by_value(Select(loc), val.value)


@select.method((object, basestring))
@select.method((object, ByText))
def _select_str(loc, s):
    return select_by_text(Select(loc), str(s))


@select.method((object, Iterable))
def _select_iter(loc, items):
    return [select(loc, item) for item in items]


def _sel_desel(el, getter_fn, setter_attr, item):
    if item is not None:
        old_item = getter_fn(el)
        if old_item != item:
            getattr(el, setter_attr)(item)
            wait_for_ajax()
        return old_item


def select_by_text(select_element, txt):
    """
    Works on a select element and selects an option by the visible text.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The select element option's visible text.

    Returns: previously selected text
    """
    def _getter(s):
        try:
            return s.first_selected_option.text
        except NoSuchElementException:
            return None
    return _sel_desel(select_element, _getter,
                      'select_by_visible_text', txt)


def select_by_value(select_element, val):
    """
    Works on a select element and selects an option by the value attribute.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        value: The select element's option value.
    """
    return _sel_desel(select_element, lambda s: ByValue(value(s)), 'select_by_value', val)


def deselect_by_text(select_element, txt):
    """
    Works on a select element and deselects an option by the visible text.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        text: The select element option's visible text.
    """
    return _sel_desel(select_element, lambda s: s.first_selected_option.text,
                      'deselect_by_visible_text', txt)


def deselect_by_value(select_element, val):
    """
    Works on a select element and deselects an option by the value attribute.

    Args:
        loc: A locator, expects either a string, WebElement, tuple.
        value: The select element's option value.
    """
    return _sel_desel(select_element, lambda s: ByValue(value(s)), 'deselect_by_value', val)


@multidispatch
def deselect(loc, o):
    raise NotImplementedError('Unable to select {} in this type: {}'.format(o, loc))


@deselect.method((object, ByValue))
def _deselect_val(loc, val):
    return deselect_by_value(Select(loc), val.value)


@deselect.method((object, basestring))
@deselect.method((object, ByText))
def _deselect_text(loc, s):
    return deselect_by_text(Select(loc), str(s))


@deselect.method((object, Iterable))
def _deselect_iter(loc, items):
    return [deselect(loc, item) for item in items]


def execute_script(script, *args, **kwargs):
    """Wrapper for execute_script() to not have to pull browser() from somewhere.

    It also provides our library which is stored in data/lib.js file.
    """
    return browser().execute_script(dedent(script), *args, **kwargs)
