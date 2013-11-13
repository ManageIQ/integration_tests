import pytest
import threading
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
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
    from selenium.webdriver.remote.webelement import WebElement

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


# Some convenience methods to wrap webdriver
class Locator(object):
    '''
e    Class to represent a locator, implements 'element'
    which is a property that any object can implement
    '''
    def __init__(self, by, value):
        self.by = by
        self.value = value
        
    @property
    def element(self):
        return browser().find_element(self.by, self.value)


def values_to_locators(dct):
    '''
    takes a dict of locators (mapping strings to tuples)
    returns a dict with the values replaced by Locators
    '''
    return {key: Locator(*value) for (key, value) in dct.items()}


def wait_for_ajax():
    WebDriverWait(browser(), 120.0)\
        .until(lambda s: s.execute_script(ajax_wait_js) == 0,
               "Ajax wait timed out")


def click(loc):
    ActionChains(browser()).move_to_element(loc.element).click().perform()
    wait_for_ajax()


def is_displayed(loc):
    try:
        return loc.element.is_displayed()
    except NoSuchElementException:
        return False


def move_to_element(loc):
    ActionChains(browser()).move_to_element(loc.element).perform()


def text(loc):
    return loc.element.text


def get_attribute(loc, attr):
    return loc.element.get_attribute(attr)


def send_keys(loc, text):
    loc.element.send_keys(text)
    wait_for_ajax()


def current_url():
    return browser().current_url
