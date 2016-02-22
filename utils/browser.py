"""Core functionality for starting, restarting, and stopping a selenium browser."""
import atexit
import json
import os
import threading
import urllib2
from contextlib import contextmanager
from shutil import rmtree
from string import Template
from tempfile import mkdtemp
from threading import Timer

import requests
from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException, WebDriverException
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.remote.file_detector import UselessFileDetector

from fixtures.pytest_store import store, write_line
from utils import conf, tries
from utils.log import logger
from utils.path import data_path

# Conditional guards against getting a new thread_locals when this module is reloaded.
if 'thread_locals' not in globals():
    # New threads get their own browser instances
    thread_locals = threading.local()
    thread_locals.browser = None
    thread_locals.wharf = None


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


def wharf():
    return thread_locals.wharf


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
    if thread_locals.wharf:
        thread_locals.wharf.renew()
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
        base_url = store.base_url

    # Pull in browser kwargs from browser yaml
    browser_kwargs = browser_conf.get('webdriver_options', {})

    # Handle firefox profile for Firefox or Remote webdriver
    if webdriver_name == 'Firefox':
        browser_kwargs['firefox_profile'] = _load_firefox_profile()
    elif (webdriver_name == 'Remote' and
          browser_kwargs['desired_capabilities']['browserName'] == 'firefox'):
        browser_kwargs['browser_profile'] = _load_firefox_profile()

    # Update it with passed-in options/overrides
    browser_kwargs.update(kwargs)

    if webdriver_name != 'Remote' and 'desired_capabilities' in browser_kwargs:
        # desired_capabilities is only for Remote driver, but can sneak in
        del(browser_kwargs['desired_capabilities'])

    if webdriver_name == 'Remote' and 'webdriver_wharf' in browser_conf and not thread_locals.wharf:
        # Configured to use wharf, but it isn't configured yet; check out a webdriver container
        wharf = Wharf(browser_conf['webdriver_wharf'])
        # TODO: Error handling! :D
        wharf.checkout()
        atexit.register(wharf.checkin)
        thread_locals.wharf = wharf

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

    if thread_locals.wharf:
        # Wharf is configured, make sure to use its command_executor
        wharf_config = thread_locals.wharf.config
        browser_kwargs['command_executor'] = wharf_config['webdriver_url']
        view_msg = 'tests can be viewed via vnc on display %s' % wharf_config['vnc_display']
        logger.info('webdriver command executor set to %s' % wharf_config['webdriver_url'])
        logger.info(view_msg)
        write_line(view_msg, cyan=True)

    try:
        browser = tries(3, WebDriverException, webdriver_class, **browser_kwargs)
        browser.file_detector = UselessFileDetector()
        browser.maximize_window()
        browser.get(base_url)
        thread_locals.browser = browser
    except urllib2.URLError as ex:
        # connection to selenium was refused for unknown reasons
        if thread_locals.wharf:
            # If we're running wharf, try again with a new container
            logger.error('URLError connecting to selenium; recycling container. URLError:')
            # Plus, since this is a really weird thing that we need to figure out,
            # throw a message out to the terminal for visibility
            write_line('URLError caused container recycle, see log for details', red=True)
            logger.exception(ex)
            thread_locals.wharf.checkin()
            thread_locals.wharf = None
            start(webdriver_name, base_url, **kwargs)
        else:
            # If we aren't running wharf, raise it
            raise

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

    browser = start(*args, **kwargs)
    try:
        yield browser
    finally:
        quit()


def _load_firefox_profile():
    # create a firefox profile using the template in data/firefox_profile.js.template
    global firefox_profile_tmpdir

    # Make a new firefox profile dir if it's unset or doesn't exist for some reason
    if firefox_profile_tmpdir is None or not os.path.exists(firefox_profile_tmpdir):
        firefox_profile_tmpdir = mkdtemp(prefix='firefox_profile_')
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

    def checkout(self):
        response = requests.get(os.path.join(self.wharf_url, 'checkout'))
        try:
            checkout = json.loads(response.content)
        except ValueError:
            raise ValueError("JSON could not be decoded:\n{}".format(response.content))
        self.docker_id = checkout.keys()[0]
        self.config = checkout[self.docker_id]
        self._reset_renewal_timer()
        logger.info('Checked out webdriver container %s' % self.docker_id)
        return self.docker_id

    def checkin(self):
        if self.docker_id:
            requests.get(os.path.join(self.wharf_url, 'checkin', self.docker_id))
            logger.info('Checked in webdriver container %s' % self.docker_id)
            self.docker_id = None

    def renew(self):
        # If we have a docker id, renew_timer shouldn't still be None
        if self.docker_id and not self.renew_timer.is_alive():
            # You can call renew as frequently as desired, but it'll only run if
            # the renewal timer has stopped or failed to renew
            response = requests.get(os.path.join(self.wharf_url, 'renew', self.docker_id))
            try:
                expiry_info = json.loads(response.content)
            except ValueError:
                raise ValueError("JSON could not be decoded:\n{}".format(response.content))
            self.config.update(expiry_info)
            self._reset_renewal_timer()
            logger.info('Renewed webdriver container %s' % self.docker_id)

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

atexit.register(quit)
