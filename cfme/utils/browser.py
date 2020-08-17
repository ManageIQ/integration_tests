"""Core functionality for starting, restarting, and stopping a selenium browser."""
import atexit
import json
import os
import threading
import time
from collections import namedtuple
from shutil import rmtree
from string import Template
from tempfile import mkdtemp
from urllib.error import URLError

import requests
from cached_property import cached_property
from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common import keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.remote.file_detector import UselessFileDetector
from werkzeug.local import LocalProxy

from cfme.fixtures.pytest_store import store
from cfme.fixtures.pytest_store import write_line
from cfme.utils import clear_property_cache
from cfme.utils import conf
from cfme.utils import tries
from cfme.utils.log import logger as log  # TODO remove after artifactor handler
from cfme.utils.path import data_path

# import logging
# log = logging.getLogger('cfme.browser')


FIVE_MINUTES = 5 * 60
THIRTY_SECONDS = 30

BROWSER_ERRORS = URLError, WebDriverException
WHARF_OUTER_RETRIES = 2


def _load_firefox_profile():
    # create a firefox profile using the template in data/firefox_profile.js.template

    # Make a new firefox profile dir if it's unset or doesn't exist for some reason
    firefox_profile_tmpdir = mkdtemp(prefix='firefox_profile_')
    log.debug("created firefox profile")
    # Clean up tempdir at exit
    atexit.register(rmtree, firefox_profile_tmpdir, ignore_errors=True)

    template = data_path.join('firefox_profile.js.template').read()
    profile_json = Template(template).substitute(profile_dir=firefox_profile_tmpdir)
    profile_dict = json.loads(profile_json)

    profile = FirefoxProfile(firefox_profile_tmpdir)
    [profile.set_preference(*pref) for pref in profile_dict.items()]
    profile.update_preferences()
    return profile


class Wharf:
    # class level to allow python level atomic removal of instance values
    docker_id = None

    def __init__(self, wharf_url):
        self.wharf_url = wharf_url
        self._renew_thread = None

    def _get(self, *args):

        response = requests.get(os.path.join(self.wharf_url, *args))
        if response.status_code == 204:
            return
        try:
            return json.loads(response.content)
        except ValueError:
            raise ValueError(
                f"JSON could not be decoded:\n{response.content}")

    def checkout(self):
        if self.docker_id is not None:
            return self.docker_id
        checkout = self._get('checkout')
        self.docker_id, self.config = next(iter(list(checkout.items())))
        self._start_renew_thread()
        log.info('Checked out webdriver container %s', self.docker_id)
        log.debug("%r", checkout)
        return self.docker_id

    def checkin(self):
        # using dict pop to avoid race conditions
        my_id = self.__dict__.pop('docker_id', None)
        if my_id:
            self._get('checkin', my_id)
            log.info('Checked in webdriver container %s', my_id)
            self._renew_thread = None

    def _start_renew_thread(self):
        assert self._renew_thread is None
        self._renew_thread = threading.Thread(target=self._renew_function)
        self._renew_thread.daemon = True
        self._renew_thread.start()

    def _renew_function(self):
        # If we have a docker id, renew_timer shouldn't still be None
        log.debug("renew thread started")
        while True:
            time.sleep(FIVE_MINUTES)
            if self._renew_thread is not threading.current_thread():
                log.debug("renew done %s is not %s",
                          self._renew_thread, threading.current_thread())
                return
            if self.docker_id is None:
                log.debug("renew done, docker id %s", self.docker_id)
                return
            expiry_info = self._get('renew', self.docker_id)
            self.config.update(expiry_info)
            log.info('Renewed webdriver container %s', self.docker_id)

    def __bool__(self):
        return self.docker_id is not None


class BrowserFactory:
    def __init__(self, webdriver_class, browser_kwargs):
        self.webdriver_class = webdriver_class
        self.browser_kwargs = browser_kwargs

        self._add_missing_options()

    def _add_missing_options(self):
        if self.webdriver_class is not webdriver.Remote:
            # desired_capabilities is only for Remote driver, but can sneak in
            self.browser_kwargs.pop('desired_capabilities', None)
        elif self.browser_kwargs['desired_capabilities']['browserName'] == 'firefox':
            self.browser_kwargs['browser_profile'] = self._firefox_profile

        if self.webdriver_class is webdriver.Firefox:
            self.browser_kwargs['firefox_profile'] = self._firefox_profile

    @cached_property
    def _firefox_profile(self):
        return _load_firefox_profile()

    def processed_browser_args(self):
        self._add_missing_options()
        return self.browser_kwargs

    def create(self, url_key):
        try:
            browser = tries(
                2, WebDriverException,
                self.webdriver_class, **self.processed_browser_args())
        except URLError as e:
            if e.reason.errno == 111:
                # Known issue
                raise RuntimeError('Could not connect to Selenium server. Is it up and running?')
            else:
                # Unknown issue
                raise

        browser.file_detector = UselessFileDetector()
        browser.maximize_window()
        browser.get(url_key)
        browser.url_key = url_key
        return browser

    def close(self, browser):
        if browser:
            browser.quit()
            clear_property_cache(self, '_firefox_profile')


class WharfFactory(BrowserFactory):
    def __init__(self, webdriver_class, browser_kwargs, wharf):
        super().__init__(webdriver_class, browser_kwargs)
        self.wharf = wharf

        if browser_kwargs.get('desired_capabilities', {}).get('browserName') == 'chrome':
            # chrome uses containers to sandbox the browser, and we use containers to
            # run chrome in wharf, so disable the sandbox if running chrome in wharf
            co = browser_kwargs['desired_capabilities'].get('chromeOptions', {})
            args = ['--no-sandbox', '--start-maximized', '--disable-extensions', 'disable-infobars']
            if 'args' not in co:
                co['args'] = args
            else:
                co['args'] = list(set(co['args'].extend(args)))
            browser_kwargs['desired_capabilities']['chromeOptions'] = co

    def processed_browser_args(self):
        command_executor = self.wharf.config['webdriver_url']
        view_msg = 'tests can be viewed via vnc on display {}'.format(
            self.wharf.config['vnc_display'])
        log.info('webdriver command executor set to %s', command_executor)
        log.info(view_msg)
        write_line(view_msg, cyan=True)
        return dict(
            super().processed_browser_args(),
            command_executor=command_executor,
        )

    def create(self, url_key):

        def inner():
            try:
                self.wharf.checkout()
                return super(WharfFactory, self).create(url_key)
            except URLError as ex:
                # connection to selenum was refused for unknown reasons
                log.error('URLError connecting to selenium; recycling container. URLError:')
                write_line('URLError caused container recycle, see log for details', red=True)
                log.exception(ex)
                self.wharf.checkin()
                raise
            except Exception:
                log.exception("failure on webdriver usage, returning container")
                self.wharf.checkin()
                raise

        return tries(WHARF_OUTER_RETRIES, BROWSER_ERRORS, inner)

    def close(self, browser):
        try:
            super().close(browser)
        finally:
            self.wharf.checkin()


class BrowserManager:
    def __init__(self, browser_factory):
        self.factory = browser_factory
        self.browser = None
        self._browser_renew_thread = None

    def coerce_url_key(self, key):
        return key or store.current_appliance.url  # TODO: don't rely on store.current_appliance

    @classmethod
    def from_conf(cls, browser_conf):
        webdriver_name = browser_conf.get('webdriver', 'Firefox')
        webdriver_class = getattr(webdriver, webdriver_name)

        browser_kwargs = browser_conf.get('webdriver_options', {})

        if 'webdriver_wharf' in browser_conf:
            wharf = Wharf(browser_conf['webdriver_wharf'])
            atexit.register(wharf.checkin)
            if browser_conf[
                'webdriver_options'][
                    'desired_capabilities']['browserName'].lower() == 'firefox':
                browser_kwargs['desired_capabilities']['marionette'] = True
                browser_kwargs['desired_capabilities']['acceptInsecureCerts'] = True
            return cls(WharfFactory(webdriver_class, browser_kwargs, wharf))
        else:
            if webdriver_name.lower() == "remote":
                if browser_conf[
                        'webdriver_options'][
                            'desired_capabilities']['browserName'].lower() == 'chrome':
                    browser_kwargs['desired_capabilities'].setdefault('chromeOptions', {})
                    browser_kwargs[
                        'desired_capabilities']['chromeOptions']['args'] = ['--no-sandbox',
                                                                            '--start-maximized',
                                                                            '--disable-extensions',
                                                                            'disable-infobars']
                    browser_kwargs['desired_capabilities'].pop('marionette', None)
                if browser_conf[
                        'webdriver_options'][
                            'desired_capabilities']['browserName'].lower() == 'firefox':
                    browser_kwargs['desired_capabilities']['marionette'] = True
                    browser_kwargs['desired_capabilities']['acceptInsecureCerts'] = True

            return cls(BrowserFactory(webdriver_class, browser_kwargs))

    def _is_alive(self):
        log.debug("alive check")
        try:
            self.browser.current_url
        except UnexpectedAlertPresentException:
            # We shouldn't think that an Unexpected alert means the browser is dead
            return True
        except Exception:
            log.exception("browser in unknown state, considering dead")
            return False
        return True

    def ensure_open(self, url_key=None):
        url_key = self.coerce_url_key(url_key)
        if getattr(self.browser, 'url_key', None) != url_key:
            return self.start(url_key=url_key)

        if self._is_alive():
            return self.browser
        else:
            return self.start(url_key=url_key)

    def add_cleanup(self, callback):
        assert self.browser is not None
        try:
            cl = self.browser.__cleanup
        except AttributeError:
            cl = self.browser.__cleanup = []
        cl.append(callback)

    def _consume_cleanups(self):
        try:
            cl = self.browser.__cleanup
        except AttributeError:
            pass
        else:
            while cl:
                cl.pop()()

    def quit(self):
        # TODO: figure if we want to log the url key here
        self._consume_cleanups()
        try:
            self.factory.close(self.browser)
        except Exception as e:
            log.error('An exception happened during browser shutdown:')
            log.exception(e)
        finally:
            self.browser = None

    def start(self, url_key=None):
        log.info('starting browser')
        url_key = self.coerce_url_key(url_key)
        if self.browser is not None:
            self.quit()
        return self.open_fresh(url_key=url_key)

    def open_fresh(self, url_key=None):
        url_key = self.coerce_url_key(url_key)
        log.info('starting browser for %r', url_key)
        assert self.browser is None

        self.browser = self.factory.create(url_key=url_key)
        return self.browser


class WithZoom:
    """
    This class is a decorator that used to wrap function with zoom level.
    this class perform zoom by <level>, call the target function and exit
    by zooming back to the original zoom level.

    Args:
        * level: int, the zooming value (i.e. -2 -> 2 clicks out; 3 -> 3 clicks in)
    """
    def __init__(self, level):
        self._level = level

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            ensure_browser_open()
            with self:
                return func(*args, **kwargs)
        return wrapper

    def __enter__(self, *args, **kwargs):
        ac = ActionChains(browser())
        for _ in range(abs(self._level)):
            ac.send_keys(keys.Keys.CONTROL,
                         keys.Keys.SUBTRACT if self._level < 0 else keys.Keys.ADD)
        ac.perform()

    def __exit__(self, *args, **kwargs):
        ac = ActionChains(browser())
        for _ in range(abs(self._level)):
            ac.send_keys(keys.Keys.CONTROL,
                         keys.Keys.SUBTRACT if -self._level < 0 else keys.Keys.ADD)
        ac.perform()


manager = BrowserManager.from_conf(conf.env.get('browser', {}))

driver = LocalProxy(manager.ensure_open)


def browser():
    """callable that will always return the current browser instance

    If ``None``, no browser is running.

    Returns:

        The current browser instance.

    """
    return manager.browser


def ensure_browser_open(url_key=None):
    """Ensures that there is a browser instance currently open

    Will reuse an existing browser or start a new one as-needed

    Returns:

        The current browser instance.

    """
    if not url_key:
        from cfme.utils.appliance import current_appliance
        url_key = current_appliance.server.address()
    return manager.ensure_open(url_key=url_key)


def start(url_key=None):
    """Starts a new web browser

    If a previous browser was open, it will be closed before starting the new browser

    Args:
    """
    # Try to clean up an existing browser session if starting a new one
    return manager.start(url_key=url_key)


def quit():
    """Close the current browser

    Will silently fail if the current browser can't be closed for any reason.

    .. note::
        If a browser can't be closed, it's usually because it has already been closed elsewhere.

    """
    manager.quit()


ScreenShot = namedtuple("screenshot", ['png', 'error'])


def take_screenshot():
    screenshot = None
    screenshot_error = None
    try:
        screenshot = browser().get_screenshot_as_base64()
    except (AttributeError, WebDriverException):
        # See comments utils.browser.ensure_browser_open for why these two exceptions
        screenshot_error = 'browser error'
    except Exception as ex:
        # If this fails for any other reason,
        # leave out the screenshot but record the reason
        if str(ex):
            screenshot_error = '{}: {}'.format(type(ex).__name__, str(ex))
        else:
            screenshot_error = type(ex).__name__
    return ScreenShot(screenshot, screenshot_error)


atexit.register(manager.quit)
