"""Core functionality for starting, restarting, and stopping a selenium browser."""
import atexit
import json
import threading
from contextlib import contextmanager
from shutil import rmtree
from string import Template
from tempfile import mkdtemp

from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

from utils import conf
from utils.path import data_path

# Conditional guards against getting a new thread_locals when this module is reloaded.
if 'thread_locals' not in globals():
    # New threads get their own browser instances
    thread_locals = threading.local()
    thread_locals.browser = None


#: After starting a firefox browser, this will be set to the temporary
#: directory where files are downloaded.
firefox_profile_tmpdir = None


def browser():
    """callable that will always return the current browser instance

    If ``None``, no browser is running.

    Returns:

        The current browser instance.

    """
    return thread_locals.browser


def ensure_browser_open():
    """Ensures that there is a browser instance currently open

    Will reuse an existing browser or start a new one as-needed

    Returns:

        The current browser instance.

    """
    try:
        browser().current_url
    except UnexpectedAlertPresentException:
        # Try to handle an open alert, restart the browser if possible
        try:
            browser().switch_to_alert().dismiss()
        except:
            start()
    except:
        # If we couldn't poke the browser for any other reason, start a new one
        start()

    return browser()


def start(webdriver_name=None, base_url=None, **kwargs):
    """Starts a new web browser

    If a previous browser was open, it will be closed before starting the new browser

    Args:
        webdriver_name: The name of the selenium Webdriver to use. Default: 'Firefox'
        base_url: Optional, will use ``utils.conf.env['base_url']`` by default
        **kwargs: Any additional keyword arguments will be passed to the webdriver constructor

    """
    # Try to clean up an existing browser session if starting a new one
    if thread_locals.browser is not None:
        quit()

    browser_conf = conf.env.get('browser', {})

    if webdriver_name is None:
        # If unset, look to the config for the webdriver type
        # defaults to Firefox
        webdriver_name = browser_conf.get('webdriver', 'Firefox')
        webdriver_class = getattr(webdriver, webdriver_name)

    if base_url is None:
        base_url = conf.env['base_url']

    # Pull in browser kwargs from browser yaml
    browser_kwargs = browser_conf.get('webdriver_options', {})

    # Handle firefox profile for Firefox or Remote webdriver
    if webdriver_name == 'Firefox' or (
            webdriver_name == 'Remote' and
            browser_kwargs['desired_capabilities']['browserName'] == 'firefox'):
        browser_kwargs['firefox_profile'] = _load_firefox_profile()

    # Update it with passed-in options/overrides
    browser_kwargs.update(kwargs)

    if webdriver_name != 'Remote' and 'desired_capabilities' in browser_kwargs:
        # desired_capabilities is only for Remote driver, but can sneak in
        del(browser_kwargs['desired_capabilities'])

    browser = webdriver_class(**browser_kwargs)
    browser.maximize_window()
    browser.get(base_url)
    thread_locals.browser = browser

    return thread_locals.browser


def quit():
    """Close the current browser

    Will silently fail if the current browser can't be closed for any reason.

    .. note::
        If a browser can't be closed, it's usually because it has already been closed elsewhere.

    """
    try:
        browser().quit()
    except:
        # Due to the multitude of exceptions can be thrown when attempting to kill the browser,
        # Diaper Pattern!
        pass
    finally:
        thread_locals.browser = None


@contextmanager
def browser_session(*args, **kwargs):
    """A context manager that can be used to start and stop a browser.

    Usage:

        with browser_session as browser:
            # do stuff with browser here
        # Browser will be closed here

    """
    conf.env['base_url'] = kwargs['base_url']
    browser = start(*args, **kwargs)
    try:
        yield browser
    finally:
        quit()
        conf.clear()


def _load_firefox_profile():
    # create a firefox profile using the template in data/firefox_profile.js.template
    global firefox_profile_tmpdir
    if firefox_profile_tmpdir is None:
        firefox_profile_tmpdir = mkdtemp(prefix='firefox_profile_')
        # Clean up tempdir at exit
        atexit.register(rmtree, firefox_profile_tmpdir)

    template = data_path.join('firefox_profile.js.template').read()
    profile_json = Template(template).substitute(profile_dir=firefox_profile_tmpdir)
    profile_dict = json.loads(profile_json)

    profile = FirefoxProfile(firefox_profile_tmpdir)
    for pref in profile_dict.iteritems():
        profile.set_preference(*pref)
    profile.update_preferences()
    return profile


class DuckwebQaTestSetup(object):
    """A standin for mozwebqa's TestSetup class

    Pretends to be a mozwebqa TestSetup so we can uninstall mozwebqa whithout
    breaking old tests that aren't yet converted.

    .. note::
        This should never be used, and places where it's currently used should stop it.

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
atexit.register(quit)
