import pytest
import threading
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from contextlib import contextmanager
import fixtures.configuration as conf
# Some thread local storage that only gets set up
# once, won't get blown away when reloading module
# Thread locals are for testing in parallel - each
# thread will get a different selenium session
if not 'thread_locals' in globals():
    thread_locals = threading.local()


def browser():
    return thread_locals.selenium


def baseurl():
    return conf.get()['selenium']['baseurl']


@contextmanager
def selenium_session(cls, *args, **kwargs):
    sel = cls(*args, **kwargs)
    thread_locals.selenium = sel
    sel.maximize_window()
    sel.get(baseurl())
    yield sel
    sel.quit()


@pytest.yield_fixture
def selenium(*args, **kwargs):
    with selenium_session(webdriver.Firefox) as sel:
        yield sel


def highlight(element):
    """Highlights (blinks) a Webdriver element.
        In pure javascript, as suggested by https://github.com/alp82.
    """
    browser().execute_script("""
            element = arguments[0];
            original_style = element.getAttribute('style');
            element.setAttribute('style', original_style + "; background: yellow;");
            setTimeout(function(){
                element.setAttribute('style', original_style);
            }, 30);
            """, element)


def pytest_configure(config):
    conf.init()

    def _execute(self, command, params=None):
        highlight(self)
        return self._old_execute(command, params)

    # Let's add highlight as a method to WebDriver so we can call it arbitrarily
    WebElement.highlight = highlight
    WebElement._old_execute = WebElement._execute
    WebElement._execute = _execute


ajax_wait_js = """
var errfn = function(f,n) { try { return f(n) } catch(e) {return 0}};
return errfn(function(n) { return jQuery.active }) +
errfn(function(n) { return Ajax.activeRequestCount });
"""


def elements(o):
    '''Convert o to list of matching WebElements. Strings are considered xpath.'''
    t = type(o)
    if t == str:
        return browser().find_elements_by_xpath(o)
    elif t == WebElement:
        return [o]
    elif t == tuple:
        return browser().find_elements(*o)
    else:
        raise TypeError("Don't know how to convert {} to WebElement.".format(o))


def element(o):
    matches = elements(o)
    if not matches:
        raise ValueError("Element {} not found on page.".format(o))
    return elements(o)[0]


def wait_for_ajax():
    WebDriverWait(browser(), 120.0)\
        .until(lambda s: s.execute_script(ajax_wait_js) == 0,
               "Ajax wait timed out")


def click(loc):
    ActionChains(browser()).move_to_element(element(loc)).click().perform()
    wait_for_ajax()


def is_displayed(loc):
    try:
        return element(loc).is_displayed()
    except NoSuchElementException:
        return False


def move_to_element(loc):
    ActionChains(browser()).move_to_element(element(loc)).perform()


def text(loc):
    return element(loc).text


def get_attribute(loc, attr):
    return element(loc).get_attribute(attr)


def send_keys(loc, text):
    element(loc).send_keys(text)
    wait_for_ajax()


def current_url():
    return browser().current_url
