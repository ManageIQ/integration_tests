import os
import time
from inspect import isclass

from cached_property import cached_property
from jsmin import jsmin
from navmazing import Navigate
from navmazing import NavigateStep
from selenium.common.exceptions import NoSuchElementException
from widgetastic.browser import Browser
from widgetastic.browser import DefaultPlugin

from cfme import exceptions
from cfme.fixtures.pytest_store import store
from cfme.utils.appliance.implementations import Implementation
from cfme.utils.appliance.implementations.common import HandleModalsMixin
from cfme.utils.browser import manager
from cfme.utils.log import create_sublogger
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


class MiqSSUIBrowser(HandleModalsMixin, Browser):
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
        # TODO: Use the same base class for both UI & SSUI since they are 99% the same
        self.logger.info(
            'Opened browser %s %s',
            selenium.capabilities.get('browserName', 'unknown'),
            selenium.capabilities.get('version', 'unknown'))

    @property
    def appliance(self):
        return self.extra_objects['appliance']

    def create_view(self, *args, **kwargs):
        timeout = kwargs.pop('wait', None)
        view = self.appliance.ssui.create_view(*args, **kwargs)
        if timeout:
            view.wait_displayed(timeout=timeout)
        return view

    @property
    def product_version(self):
        return self.appliance.version


class MiqSSUIBrowserPlugin(DefaultPlugin):

    ENSURE_PAGE_SAFE = jsmin('''
        try {
            var drawer = angular.element(document.getElementsByTagName("pf-notification-drawer"));
            if (drawer && drawer.is(':visible')){
                drawer.hide();
            };

            var eventNotificationsService = drawer.injector().get('eventNotifications');
            eventNotificationsService.clearAll(
                ManageIQ.angular.eventNotificationsData.state.groups[0]
            );
            eventNotificationsService.clearAll(
                ManageIQ.angular.eventNotificationsData.state.groups[1]
            );
        } catch(err) {
        }

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

    def log_message(self, msg, level="debug"):
        class_name = self.obj.__name__ if isclass(self.obj) else self.obj.__class__.__name__
        str_msg = "[SUI-NAV/{}/{}]: {}".format(class_name, self._name, msg)
        getattr(logger, level)(str_msg)

    def construct_message(self, here, resetter, view, duration, waited, force):
        str_here = "Already Here" if here else "Needed Navigation"
        str_resetter = "Resetter Used" if resetter else "No Resetter"
        str_view = "View Returned" if view else "No View Available"
        str_waited = "Waited on View" if waited else "No Wait on View"
        str_force = "Force Navigation Used" if force else "Navigation Not Forced"
        return "{here}/{resetter}/{view}/{waited}/{force} (elapsed {duration}ms)".format(
            here=str_here, resetter=str_resetter, view=str_view, waited=str_waited,
            force=str_force, duration=duration
        )

    def go(self, _tries=0, *args, **kwargs):
        nav_args = {'use_resetter': True, 'wait_for_view': 10, 'force': False}

        self.log_message("Beginning SUI Navigation...", level="info")
        start_time = time.time()
        if _tries > 2:
            # Need at least three tries:
            # 1: login_admin handles an alert or CannotContinueWithNavigation appears.
            # 2: Everything should work. If not, NavigationError.
            raise exceptions.NavigationError(self._name)

        _tries += 1
        for arg in nav_args:
            if arg in kwargs:
                nav_args[arg] = kwargs.pop(arg)
        self.pre_navigate(_tries, *args, **kwargs)

        here = False
        resetter_used = False
        waited = False
        force_used = False
        try:
            here = self.am_i_here()
        except NotImplementedError:
            nav_args['wait_for_view'] = 0
            self.log_message(
                "is_displayed not implemented for {} view".format(self.VIEW or ""), level="warn")
        except Exception as e:
            self.log_message(
                "Exception raised [{}] whilst checking if already here".format(e), level="error")

        if not here or nav_args['force']:
            if nav_args['force']:
                force_used = True
            self.log_message("Prerequisite Needed")
            self.prerequisite_view = self.prerequisite()
            self.do_nav(_tries, *args, **kwargs)
        if nav_args['use_resetter']:
            resetter_used = True
            self.resetter()
        self.post_navigate(_tries)
        view = self.view if self.VIEW is not None else None
        duration = int((time.time() - start_time) * 1000)
        if view and nav_args['wait_for_view'] and not os.environ.get(
                'DISABLE_NAVIGATE_ASSERT', False):
            waited = True
            wait_for(
                lambda: view.is_displayed, num_sec=nav_args['wait_for_view'],
                message="Waiting for view [{}] to display".format(view.__class__.__name__)
            )
        self.log_message(
            self.construct_message(here, resetter_used, view, duration, waited, force_used),
            level="info"
        )

        return view


navigator = Navigate()
navigate_to = navigator.navigate


class ViaSSUI(Implementation):

    name = "SSUI"
    navigator = navigator

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
