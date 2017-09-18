from jsmin import jsmin
from navmazing import Navigate, NavigateStep
from selenium.common.exceptions import NoSuchElementException
from widgetastic.browser import Browser, DefaultPlugin

from cached_property import cached_property
from fixtures.pytest_store import store
from cfme.utils.browser import manager
from cfme.utils.log import logger, create_sublogger
from cfme.utils.wait import wait_for

from . import Implementation


class MiqSSUIBrowser(Browser):
    def __init__(self, selenium, endpoint, extra_objects=None):
        extra_objects = extra_objects or {}
        extra_objects.update({
            'appliance': endpoint.owner,
            'endpoint': endpoint,
            'store': store,
        })
        super(MiqSSUIBrowser, self).__init__(
            selenium,
            plugin_class=MiqSSUIBrowserPlugin,
            logger=create_sublogger('MiqSSUIBrowser'),
            extra_objects=extra_objects)
        self.window_handle = selenium.current_window_handle

    @property
    def appliance(self):
        return self.extra_objects['appliance']

    def create_view(self, *args, **kwargs):
        return self.appliance.ssui.create_view(*args, **kwargs)

    @property
    def product_version(self):
        return self.appliance.version


class MiqSSUIBrowserPlugin(DefaultPlugin):

    ENSURE_PAGE_SAFE = jsmin('''
        function checkProgressBar() {
            try {
                return $('#ngProgress').attr('style').indexOf('width: 0%') > -1;
            } catch(err) {
                // Not ready yet
            return false;
            }
        }

        function checkJquery() {
            if(typeof $ == 'undefined') {
                return true;
            } else {
                return !($.active > 0);
            }
        }

        return checkProgressBar() && checkJquery();''')

    def ensure_page_safe(self, timeout='20s'):
        # THIS ONE SHOULD ALWAYS USE JAVASCRIPT ONLY, NO OTHER SELENIUM INTERACTION

        def _check():
            result = self.browser.execute_script(self.ENSURE_PAGE_SAFE, silent=True)
            # TODO: Logging
            return bool(result)

        wait_for(_check, timeout=timeout, delay=2, silent_failure=True, very_quiet=True)

    def after_keyboard_input(self, element, keyboard_input):
        self.browser.plugin.ensure_page_safe()


class SSUINavigateStep(NavigateStep):
    VIEW = None

    @cached_property
    def view(self):
        if self.VIEW is None:
            raise AttributeError('{} does not have VIEW specified'.format(type(self).__name__))
        return self.create_view(self.VIEW, additional_context={'object': self.obj})

    @property
    def appliance(self):
        return self.obj.appliance

    def create_view(self, *args, **kwargs):
        return self.appliance.ssui.create_view(*args, **kwargs)

    def am_i_here(self):
        try:
            return self.view.is_displayed
        except (AttributeError, NoSuchElementException):
            return False

    def pre_navigate(self, *args, **kwargs):
        self.appliance.browser.open_browser(url_key=self.obj.appliance.server.address())

    def do_nav(self, _tries=0, *args, **kwargs):
        """Describes how the navigation should take place."""
        try:
            self.step(*args, **kwargs)
        except Exception as e:
            logger.error(e)
            raise
            self.go(_tries, *args, **kwargs)

    def go(self, _tries=0):
        _tries += 1
        self.pre_navigate(_tries)
        logger.debug("SSUI-NAVIGATE: Checking if already at {}".format(self._name))
        here = False
        try:
            here = self.am_i_here()
        except Exception as e:
            logger.debug(
                "SSUI-NAVIGATE: Exception raised [{}] whilst checking if already at {}".format(
                    e, self._name))
        if here:
            logger.debug("SSUI-NAVIGATE: Already at {}".format(self._name))
        else:
            logger.debug("SSUI-NAVIGATE: I'm not at {}".format(self._name))
            self.prerequisite_view = self.prerequisite()
            logger.debug("SSUI-NAVIGATE: Heading to destination {}".format(self._name))
            self.do_nav(_tries)
        self.resetter()
        self.post_navigate(_tries)
        if self.VIEW is not None:
            return self.view


navigator = Navigate()
navigate_to = navigator.navigate


class ViaSSUI(Implementation):
    def __str__(self):
        return 'SSUI'

    @cached_property
    def widgetastic(self):
        """This gives us a widgetastic browser."""
        # TODO: Make this a property that could watch for browser change?
        browser = self.open_browser(url_key=self.appliance.server.address())
        wt = MiqSSUIBrowser(browser, self)
        manager.add_cleanup(self._reset_cache)
        return wt
