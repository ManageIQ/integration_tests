"""Core functionality for starting, restarting, and stopping a selenium browser."""
import atexit
import json
import os
import urllib2
import time
import threading
from shutil import rmtree
from string import Template
from tempfile import mkdtemp

# import logging

from werkzeug.local import LocalProxy

import requests
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common import keys
from selenium.common.exceptions import UnexpectedAlertPresentException, WebDriverException
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.remote.file_detector import UselessFileDetector

from cached_property import cached_property

from fixtures.pytest_store import store, write_line
from utils import conf, tries
from utils.path import data_path

from utils.log import logger as log  # TODO remove after artifactor handler
# log = logging.getLogger('cfme.browser')


FIVE_MINUTES = 5 * 60
THIRTY_SECONDS = 30


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
    for pref in profile_dict.iteritems():
        profile.set_preference(*pref)
    profile.update_preferences()
    return profile


class Wharf(object):
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
                "JSON could not be decoded:\n{}".format(response.content))

    def checkout(self):
        if self.docker_id is not None:
            return self.docker_id
        checkout = self._get('checkout')
        self.docker_id, self.config = checkout.items()[0]
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

    def __nonzero__(self):
        return self.docker_id is not None


def web_driver_class_factory(base_class, lock):
    def execute(self, *args, **kwargs):
        with lock:
            return base_class.execute(self, *args, **kwargs)
    return type(base_class.__name__, (base_class,), {"execute": execute})


class BrowserFactory(object):
    def __init__(self, webdriver_class, browser_kwargs):
        self.lock = threading.RLock()
        self.webdriver_class = web_driver_class_factory(webdriver_class, self.lock)
        self.browser_kwargs = browser_kwargs

        if webdriver_class is not webdriver.Remote:
            # desired_capabilities is only for Remote driver, but can sneak in
            browser_kwargs.pop('desired_capabilities', None)
        elif browser_kwargs['desired_capabilities']['browserName'] == 'firefox':
            browser_kwargs['browser_profile'] = self._firefox_profile

        if webdriver_class is webdriver.Firefox:
            browser_kwargs['firefox_profile'] = self._firefox_profile

    @cached_property
    def _firefox_profile(self):
        return _load_firefox_profile()

    def processed_browser_args(self):
        return self.browser_kwargs

    def create(self, url_key):
        try:
            browser = tries(
                3, WebDriverException,
                self.webdriver_class, **self.processed_browser_args())
        except urllib2.URLError as e:
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


class WharfFactory(BrowserFactory):
    def __init__(self, webdriver_class, browser_kwargs, wharf):
        super(WharfFactory, self).__init__(webdriver_class, browser_kwargs)
        self.wharf = wharf

        if browser_kwargs['desired_capabilities']['browserName'] == 'chrome':
            # chrome uses containers to sandbox the browser, and we use containers to
            # run chrome in wharf, so disable the sandbox if running chrome in wharf
            co = browser_kwargs['desired_capabilities'].get('chromeOptions', {})
            arg = '--no-sandbox'
            if 'args' not in co:
                co['args'] = [arg]
            elif arg not in co['args']:
                co['args'].append(arg)
            browser_kwargs['desired_capabilities']['chromeOptions'] = co

    def processed_browser_args(self):
        command_executor = self.wharf.config['webdriver_url']
        view_msg = 'tests can be viewed via vnc on display {}'.format(
            self.wharf.config['vnc_display'])
        log.info('webdriver command executor set to %s', command_executor)
        log.info(view_msg)
        write_line(view_msg, cyan=True)
        return dict(
            super(WharfFactory, self).processed_browser_args(),
            command_executor=command_executor,
        )

    def create(self, url_key):

        def inner():
            try:
                self.wharf.checkout()
                return super(WharfFactory, self).create(url_key)
            except urllib2.URLError as ex:
                # connection to selenum was refused for unknown reasons
                log.error('URLError connecting to selenium; recycling container. URLError:')
                write_line('URLError caused container recycle, see log for details', red=True)
                log.exception(ex)
                self.wharf.checkin()
                raise
        return tries(10, urllib2.URLError, inner)

    def close(self, browser):
        try:
            super(WharfFactory, self).close(browser)
        finally:
            self.wharf.checkin()


class BrowserKeepAliveThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, manager):
        super(BrowserKeepAliveThread, self).__init__()
        self._stop = threading.Event()
        self.manager = manager

    def run(self):
        while not self.stopped():
            time.sleep(THIRTY_SECONDS)
            with self.manager.factory.lock:

                # The double try is necessary as if the purpose of the function is to ensure that
                # the connection doesn't die. If the connection does die due to lack of interaction
                # then this double try will fail the first time and connect the second time.
                # The break ensures we don't run the call more times than we need to.
                for _ in range(2):
                    try:
                        log.debug('renew')
                        self.manager.browser.current_url
                        break
                    except Exception as e:
                        log.error('something bad happened')
                        log.error(e)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class BrowserManager(object):
    def __init__(self, browser_factory):
        self.factory = browser_factory
        self.browser = None
        self._browser_renew_thread = None

    def coerce_url_key(self, key):
        return key or store.base_url

    @classmethod
    def from_conf(cls, browser_conf):
        webdriver_name = browser_conf.get('webdriver', 'Firefox')
        webdriver_class = getattr(webdriver, webdriver_name)

        browser_kwargs = browser_conf.get('webdriver_options', {})

        if 'webdriver_wharf' in browser_conf:
            wharf = Wharf(browser_conf['webdriver_wharf'])
            atexit.register(wharf.checkin)
            return cls(WharfFactory(webdriver_class, browser_kwargs, wharf))
        else:
            return cls(BrowserFactory(webdriver_class, browser_kwargs))

    def _browser_start_renew_thread(self):
        log.debug('starting repeater')
        self._browser_renew_thread = BrowserKeepAliveThread(self)
        self._browser_renew_thread.daemon = True
        self._browser_renew_thread.start()

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
        log.info('closing browser')
        self._consume_cleanups()
        try:
            self.factory.close(self.browser)
        except Exception as e:
            log.error('An exception happened during browser shutdown:')
            log.exception(e)
        finally:
            self.browser = None
            if self._browser_renew_thread:
                self._browser_renew_thread.stop()
                self._browser_renew_thread = None

    def start(self, url_key=None):
        log.info('starting browser')
        url_key = self.coerce_url_key(url_key)
        if self.browser is not None:
            self.quit()
        self._browser_start_renew_thread()
        return self.open_fresh(url_key=url_key)

    def open_fresh(self, url_key=None):
        url_key = self.coerce_url_key(url_key)
        log.info('starting browser for %r', url_key)
        assert self.browser is None

        self.browser = self.factory.create(url_key=url_key)
        return self.browser


class WithZoom(object):
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
        for _ in xrange(abs(self._level)):
            ac.send_keys(keys.Keys.CONTROL,
                         keys.Keys.SUBTRACT if self._level < 0 else keys.Keys.ADD)
        ac.perform()

    def __exit__(self, *args, **kwargs):
        ac = ActionChains(browser())
        for _ in xrange(abs(self._level)):
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


atexit.register(manager.quit)
