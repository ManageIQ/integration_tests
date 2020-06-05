"""Core functionality for starting, restarting, and stopping a selenium browser."""
import atexit
import json
from collections import namedtuple
from shutil import rmtree
from string import Template
from tempfile import mkdtemp

import attr
from cached_property import cached_property
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common import keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from webdriver_kaifuku import BrowserFactory as KaifukuBrowserFactory
from webdriver_kaifuku import BrowserManager as KaifukuBrowserManager
from webdriver_kaifuku import WharfFactory as KaifukuWharfFactory

from cfme.fixtures.pytest_store import write_line
from cfme.utils import clear_property_cache
from cfme.utils import conf
from cfme.utils.log import logger
from cfme.utils.path import data_path


@attr.s
class BrowserFactory(KaifukuBrowserFactory):
    """Override some behavior in Kaifuku for MIQ customization"""
    def __attr_post_init__(self):
        super().__attr_post_init__()
        if self.browser_kwargs['desired_capabilities']['browserName'] == 'firefox':
            self.browser_kwargs['browser_profile'] = self._firefox_profile

        if self.webdriver_class is webdriver.Firefox:
            self.browser_kwargs['firefox_profile'] = self._firefox_profile

    @cached_property
    def _firefox_profile(self):
        # create a firefox profile using the template in data/firefox_profile.js.template

        # Make a new firefox profile dir if it's unset or doesn't exist for some reason
        firefox_profile_tmpdir = mkdtemp(prefix='firefox_profile_')
        logger.debug("created firefox profile")
        # Clean up tempdir at exit
        atexit.register(rmtree, firefox_profile_tmpdir, ignore_errors=True)

        template = data_path.join('firefox_profile.js.template').read()
        profile_json = Template(template).substitute(profile_dir=firefox_profile_tmpdir)
        profile_dict = json.loads(profile_json)

        profile = FirefoxProfile(firefox_profile_tmpdir)
        [profile.set_preference(*pref) for pref in profile_dict.items()]
        profile.update_preferences()
        return profile

    def close(self, browser):
        super().close(browser)
        clear_property_cache(self, '_firefox_profile')


@attr.s
class WharfFactory(KaifukuWharfFactory):
    """Override some behavior in Kaifuku for MIQ customization"""
    DEFAULT_WHARF_CHROME_OPT_ARGS = [
        '--no-sandbox',
        '--start-maximized',
        '--disable-extensions',
        '--disable-infobars'
    ]

    def processed_browser_args(self):
        parent_return = super().processed_browser_args()
        write_line('====== Selenium browser available to view tests ======', cyan=True)
        write_line(f'Wharf VNC Browser: {self.wharf.config["vnc_display"]}', cyan=True)
        return parent_return


@attr.s
class BrowserManager(KaifukuBrowserManager):
    BR_FACTORY_CLASS = BrowserFactory
    WF_FACTORY_CLASS = WharfFactory

    DEFAULT_CHROME_OPT_ARGS = [
        '--no-sandbox',
        '--start-maximized',
        '--disable-extensions',
        '--disable-infobars'
    ]

    def start_at_url(self, url):
        logger.info(f'starting browser and getting URL: "{url}"')
        if self.browser is not None:
            self.quit()
        self.open_fresh()
        self.browser.get(url)
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
            manager.ensure_open()
            with self:
                return func(*args, **kwargs)
        return wrapper

    def __enter__(self, *args, **kwargs):
        ac = ActionChains(manager.browser)
        for _ in range(abs(self._level)):
            ac.send_keys(keys.Keys.CONTROL,
                         keys.Keys.SUBTRACT if self._level < 0 else keys.Keys.ADD)
        ac.perform()

    def __exit__(self, *args, **kwargs):
        ac = ActionChains(manager.browser)
        for _ in range(abs(self._level)):
            ac.send_keys(keys.Keys.CONTROL,
                         keys.Keys.SUBTRACT if -self._level < 0 else keys.Keys.ADD)
        ac.perform()


manager = BrowserManager.from_conf(conf.env.get('browser', {}))

ScreenShot = namedtuple("screenshot", ['png', 'error'])


def take_screenshot():
    screenshot = None
    screenshot_error = None
    try:
        screenshot = manager.browser.get_screenshot_as_base64()
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
