import threading
from contextlib import contextmanager

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from utils import conf

# Conditional guards against getting a new thread_locals when this module is reloaded.
if not 'thread_locals' in globals():
    # New threads get their own browser instances
    thread_locals = threading.local()
    thread_locals.browser = None


def browser():
    return thread_locals.browser


def ensure_browser_open():
    try:
        browser().current_url
    except (AttributeError, WebDriverException):
        # AttributeError: browser() was None, didn't have current_url attr
        # WebDriverError: current_url couldn't be retrieved, browser was closed
        start()


def start(_webdriver=None, base_url=None, **kwargs):
    # Try to clean up an existing browser session if starting a new one
    if thread_locals.browser is not None:
        try:
            thread_locals.browser.quit()
        except WebDriverException:
            pass
        finally:
            thread_locals.browser = None

    if _webdriver is None:
        # If unset, look to the config for the webdriver type
        # defaults to Firefox
        _webdriver = conf.env['browser'].get('webdriver', 'Firefox')

    if isinstance(_webdriver, basestring):
        # Try to convert _webdriver str into a webdriver by name
        # e.g. 'Firefox', 'Chrome', RemoteJS', useful for interactive development
        _webdriver = getattr(webdriver, _webdriver)
    # else: implicitly assume _webdriver is a WebDriver class already

    if base_url is None:
        base_url = conf.env['base_url']

    # Pull in browser kwargs from browser yaml
    browser_kwargs = conf.env['browser'].get('webdriver_options', {})
    # Update it with passed-in options/overrides
    browser_kwargs.update(kwargs)

    browser = WebDriverWrapper(_webdriver(**browser_kwargs), base_url)
    browser.maximize_window()
    browser.get(base_url)
    thread_locals.browser = browser

    return thread_locals.browser


@contextmanager
def browser_session(*args, **kwargs):
    browser = start(*args, **kwargs)
    yield browser
    browser.quit()


class WebDriverWrapper(object):
    """Wrapper class to add custom behavior to webdrivers"""
    def __init__(self, webdriver, base_url=None):
        self._webdriver = webdriver
        self._base_url = base_url

    def __dir__(self):
        # Custom __dir__ handler to better impersonate a WebDriver
        # (basically makes tab-completion work in the python shell)
        my_dir = self.__dict__.keys() + type(self).__dict__.keys()
        wrapped_dir = dir(self._webdriver)
        return sorted(list(set(my_dir) | set(wrapped_dir)))

    def __getattr__(self, attr):
        # Try to pull the attr from this obj, and then go down to the
        # wrapped webdriver if that fails
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            _webdriver = object.__getattribute__(self, '_webdriver')
            return _webdriver.__getattribute__(attr)

    def start(self):
        return start(type(self._webdriver), self._base_url)


class DuckwebQaTestSetup(object):
    """A standin for mozwebqa's TestSetup class

    Pretends to be a mozwebqa TestSetup so we can uninstall mozwebqa whithout
    breaking old tests that aren't yet converted.

    """
    def __init__(self):
        self.selenium_client = DuckwebQaClient()
        self.base_url = conf.env['base_url']
        self.credentials = conf.credentials

    @property
    def selenium(self):
        return browser()

    @property
    def timeout(self):
        return self.selenium_client.timeout

    @property
    def default_implicit_wait(self):
        return self.selenium_client.default_implicit_wait


class DuckwebQaClient(object):
    def __init__(self):
        # These don't actually get used anywhere, they're here to help with the
        # mozwebqa spoofage only. To change timeouts and wait values, pass
        # different options to browser_session.
        self.timeout = 60
        self.default_implicit_wait = 10

    @property
    def selenium(self):
        return browser()


# Convenience name, duckwebqa is stateless, so we can just make one here
testsetup = DuckwebQaTestSetup()
