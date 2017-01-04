"""Core functionality for starting, restarting, and stopping a selenium browser."""
import atexit
import json
import os
import urllib2
from shutil import rmtree
from string import Template
from tempfile import mkdtemp
from threading import Timer
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
    def __init__(self, wharf_url):
        self.wharf_url = wharf_url
        self.docker_id = None
        self.renew_timer = None

    def _get(self, *args):
        return requests.get(os.path.join(self.wharf_url, *args))

    def checkout(self):
        if self.docker_id is not None:
            return self.docker_id
        response = self._get('checkout')
        try:
            checkout = json.loads(response.content)
        except ValueError:
            raise ValueError("JSON could not be decoded:\n{}".format(response.content))
        self.docker_id = checkout.keys()[0]
        self.config = checkout[self.docker_id]
        self._reset_renewal_timer()
        log.info('Checked out webdriver container %s', self.docker_id)
        return self.docker_id

    def checkin(self):
        if self.docker_id:
            self._get('checkin', self.docker_id)
            log.info('Checked in webdriver container %s', self.docker_id)
            self.docker_id = None

    def renew(self):
        # If we have a docker id, renew_timer shouldn't still be None
        if self.docker_id and not self.renew_timer.is_alive():
            # You can call renew as frequently as desired, but it'll only run if
            # the renewal timer has stopped or failed to renew
            response = self._get('renew', self.docker_id)
            try:
                expiry_info = json.loads(response.content)
            except ValueError:
                raise ValueError("JSON could not be decoded:\n{}".format(response.content))
            self.config.update(expiry_info)
            self._reset_renewal_timer()
            log.info('Renewed webdriver container %s', self.docker_id)

    def _reset_renewal_timer(self):
        if self.docker_id:
            if self.renew_timer:
                self.renew_timer.cancel()

            # Floor div by 2 and add a second to renew roughly halfway before expiration
            cautious_expire_interval = (self.config['expire_interval'] >> 1) + 1
            self.renew_timer = Timer(cautious_expire_interval, self.renew)
            # mark as daemon so the timer is rudely destroyed on shutdown
            self.renew_timer.daemon = True
            self.renew_timer.start()

    def __nonzero__(self):
        return bool(self.docker_id)


class BrowserFactory(object):
    def __init__(self, webdriver_class, browser_kwargs):
        self.webdriver_class = webdriver_class
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

    def renew(self):
        pass

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

    def renew(self):
        self.wharf.renew()


class SauceFactory(BrowserFactory):
    def processed_browser_args(self):
        sauce_url = self.browser_kwargs.pop('webdriver_sauce')
        command_executor = sauce_url.format(user_name=conf.credentials['saucelabs']['username'],
                                            access_key=conf.credentials['saucelabs']['access_key'])
        log.info('webdriver command executor set to %s', command_executor)
        return dict(
            super(SauceFactory, self).processed_browser_args(),
            command_executor=command_executor)


class BrowserManager(object):
    def __init__(self, browser_factory):
        self.factory = browser_factory
        self.browser = None

    def coerce_url_key(self, key):
        return key or store.base_url

    @classmethod
    def from_conf(cls, browser_conf=None):
        if not browser_conf:
            browser_conf = conf.env.get('browser', {})
        webdriver_name = browser_conf.get('webdriver', 'Firefox')
        webdriver_class = getattr(webdriver, webdriver_name)

        browser_kwargs = browser_conf.get('webdriver_options', {})

        if 'webdriver_wharf' in browser_conf:
            wharf = Wharf(browser_conf['webdriver_wharf'])
            atexit.register(wharf.checkin)
            return cls(WharfFactory(webdriver_class, browser_kwargs, wharf))
        elif 'webdriver_sauce' in browser_conf:
            browser_kwargs['webdriver_sauce'] = browser_conf['webdriver_sauce']
            return cls(SauceFactory(webdriver_class, browser_kwargs))
        else:
            return cls(BrowserFactory(webdriver_class, browser_kwargs))

    def _is_running(self, url_key):
        try:
            self.browser.current_url
        except UnexpectedAlertPresentException:
            # Try to handle an open alert, restart the browser if possible
            try:
                self.browser.switch_to_alert().dismiss()
            except:
                return False
        except:
            # If we couldn't poke the browser for any other reason, start a new one
            return False
        return True

    def ensure_open(self, url_key=None):
        url_key = self.coerce_url_key(url_key)
        if self.browser is None or self.browser.url_key != url_key:
            return self.start(url_key=url_key)

        if self._is_running(url_key):
            self.factory.renew()
        else:
            self.start(url_key=url_key)
        return self.browser

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
            self.browser.quit()
        except:
            # Due to the multitude of exceptions can be thrown when attempting to kill the browser,
            # Diaper Pattern!
            pass
        finally:
            self.browser = None

    def start(self, url_key=None):
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


class WithZoom(object):
    """This class is a decorator that used to wrap function with zoom level.
    this class perform zoom by <level>, call the target function and exit
    by zooming back to the original zoom level.
    Args:
        * level: int, the zooming value
                (i.e. -2 -> 2 clicks out; 3 -> 3 clicks in)
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


manager = BrowserManager.from_conf()

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
