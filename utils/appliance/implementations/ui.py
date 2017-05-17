# -*- coding: utf-8 -*-
import json
import time
from jsmin import jsmin
from inspect import isclass

from utils.log import logger, create_sublogger
from cfme import exceptions
from time import sleep

from navmazing import Navigate, NavigateStep
from selenium.common.exceptions import (
    ErrorInResponseException, InvalidSwitchToTargetException,
    InvalidElementStateException, WebDriverException, UnexpectedAlertPresentException,
    NoSuchElementException, StaleElementReferenceException)

from utils.browser import manager
from fixtures.pytest_store import store

from cached_property import cached_property
from widgetastic.browser import Browser, DefaultPlugin
from widgetastic.widget import Text, View
from widgetastic.utils import VersionPick
from utils.version import Version
from utils.wait import wait_for

from . import Implementation

VersionPick.VERSION_CLASS = Version


class ErrorView(View):
    title = Text("//body/h1")
    body = Text("//body/p")

    error_text = Text(
        "//h1[normalize-space(.)='Unexpected error encountered']"
        "/following-sibling::h3[not(fieldset)]"
    )

    def get_rails_error(self):
        """Gets the displayed error messages"""
        if self.browser.is_displayed("//body[./h1 and ./p and ./hr and ./address]"):
            try:
                return "{}: {}".format(self.title.text, self.body.text)
            except NoSuchElementException:
                return None
        elif self.browser.is_displayed(
                "//h1[normalize-space(.)='Unexpected error encountered']"):
            try:
                return self.error_text.text
            except NoSuchElementException:  # Just in case something goes really wrong
                return None
        return None


class MiqBrowserPlugin(DefaultPlugin):
    ENSURE_PAGE_SAFE = jsmin('''\
        function isHidden(el) {if(el === null) return true; return el.offsetParent === null;}

        try {
            angular.element('error-modal').hide();
        } catch(err) {
        }

        try {
            return ! ManageIQ.qe.anythingInFlight();
        } catch(err) {
            return (
                ((typeof $ === "undefined") ? true : $.active < 1) &&
                (
                    !((!isHidden(document.getElementById("spinner_div"))) &&
                    isHidden(document.getElementById("lightbox_div")))) &&
                document.readyState == "complete" &&
                ((typeof checkMiqQE === "undefined") ? true : checkMiqQE('autofocus') < 1) &&
                ((typeof checkMiqQE === "undefined") ? true : checkMiqQE('debounce') < 1) &&
                ((typeof checkAllMiqQE === "undefined") ? true : checkAllMiqQE() < 1)
            );
        }
        ''')

    OBSERVED_FIELD_MARKERS = (
        'data-miq_observe',
        'data-miq_observe_date',
        'data-miq_observe_checkbox',
    )
    DEFAULT_WAIT = .8

    def ensure_page_safe(self, timeout='10s'):
        # THIS ONE SHOULD ALWAYS USE JAVASCRIPT ONLY, NO OTHER SELENIUM INTERACTION

        def _check():
            result = self.browser.execute_script(self.ENSURE_PAGE_SAFE, silent=True)
            # TODO: Logging
            return bool(result)

        wait_for(_check, timeout=timeout, delay=0.2, silent_failure=True, very_quiet=True)

    def after_keyboard_input(self, element, keyboard_input):
        observed_field_attr = None
        for attr in self.OBSERVED_FIELD_MARKERS:
            observed_field_attr = self.browser.get_attribute(attr, element)
            if observed_field_attr is not None:
                break
        else:
            return

        try:
            attr_dict = json.loads(observed_field_attr)
            interval = float(attr_dict.get('interval', self.DEFAULT_WAIT))
            # Pad the detected interval, as with default_wait
            if interval < self.DEFAULT_WAIT:
                interval = self.DEFAULT_WAIT
        except (TypeError, ValueError):
            # ValueError and TypeError happens if the attribute value couldn't be decoded as JSON
            # ValueError also happens if interval couldn't be coerced to float
            # In either case, we've detected an observed text field and should wait
            self.logger.warning('could not parse %r', observed_field_attr)
            interval = self.DEFAULT_WAIT

        self.logger.debug('observed field detected, pausing for %.1f seconds', interval)
        time.sleep(interval)
        self.browser.plugin.ensure_page_safe()


class MiqBrowser(Browser):
    def __init__(self, selenium, endpoint, extra_objects=None):
        extra_objects = extra_objects or {}
        extra_objects.update({
            'appliance': endpoint.owner,
            'endpoint': endpoint,
            'store': store,
        })
        super(MiqBrowser, self).__init__(
            selenium,
            plugin_class=MiqBrowserPlugin,
            logger=create_sublogger('MiqBrowser'),
            extra_objects=extra_objects)
        self.window_handle = selenium.current_window_handle

    @property
    def appliance(self):
        return self.extra_objects['appliance']

    def create_view(self, *args, **kwargs):
        return self.appliance.browser.create_view(*args, **kwargs)

    @property
    def product_version(self):
        return self.appliance.version


def can_skip_badness_test(fn):
    """Decorator for setting a noop"""
    fn._can_skip_badness_test = True
    return fn


class CFMENavigateStep(NavigateStep):
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
        return self.appliance.browser.create_view(*args, **kwargs)

    def am_i_here(self):
        try:
            return self.view.is_displayed
        except (AttributeError, NoSuchElementException):
            return False

    def check_for_badness(self, fn, _tries, nav_args, *args, **kwargs):
        if getattr(fn, '_can_skip_badness_test', False):
            # self.log_message('Op is a Nop! ({})'.format(fn.__name__))
            return

        if self.VIEW:
            self.view.flush_widget_cache()
        go_kwargs = kwargs.copy()
        go_kwargs.update(nav_args)
        self.appliance.browser.open_browser(url_key=self.obj.appliance.server.address())

        # check for MiqQE javascript patch on first try and patch the appliance if necessary
        if self.appliance.is_miqqe_patch_candidate and not self.appliance.miqqe_patch_applied:
            self.appliance.patch_with_miqqe()
            self.appliance.browser.quit_browser()
            _tries -= 1
            self.go(_tries, *args, **go_kwargs)

        br = self.appliance.browser

        try:
            br.widgetastic.execute_script('miqSparkleOff();', silent=True)
        except:  # noqa
            # miqSparkleOff undefined, so it's definitely off.
            # Or maybe it is alerts? Let's only do this when we get an exception.
            self.appliance.browser.widgetastic.dismiss_any_alerts()
            # If we went so far, let's put diapers on one more miqSparkleOff just to be sure
            # It can be spinning in the back
            try:
                br.widgetastic.execute_script('miqSparkleOff();', silent=True)
            except:  # noqa
                pass

        # Check if the page is blocked with blocker_div. If yes, let's headshot the browser right
        # here
        if (
                br.widgetastic.is_displayed("//div[@id='blocker_div' or @id='notification']") or
                br.widgetastic.is_displayed(".modal-backdrop.fade.in")):
            logger.warning("Page was blocked with blocker div on start of navigation, recycling.")
            self.appliance.browser.quit_browser()
            self.go(_tries, *args, **go_kwargs)

        # Check if modal window is displayed
        if (br.widgetastic.is_displayed(
                "//div[contains(@class, 'modal-dialog') and contains(@class, 'modal-lg')]")):
            logger.warning("Modal window was open; closing the window")
            br.widgetastic.click(
                "//button[contains(@class, 'close') and contains(@data-dismiss, 'modal')]")

        # Check if jQuery present
        try:
            br.widgetastic.execute_script("jQuery", silent=True)
        except Exception as e:
            if "jQuery" not in str(e):
                logger.error("Checked for jQuery but got something different.")
                logger.exception(e)
            # Restart some workers
            logger.warning("Restarting UI and VimBroker workers!")
            with self.appliance.ssh_client as ssh:
                # Blow off the Vim brokers and UI workers
                ssh.run_rails_command("\"(MiqVimBrokerWorker.all + MiqUiWorker.all).each &:kill\"")
            logger.info("Waiting for web UI to come back alive.")
            sleep(10)   # Give it some rest
            self.appliance.wait_for_web_ui()
            self.appliance.browser.quit_browser()
            self.appliance.browser.open_browser(url_key=self.obj.appliance.server.address())
            self.go(_tries, *args, **go_kwargs)

        # Same with rails errors
        view = br.widgetastic.create_view(ErrorView)
        rails_e = view.get_rails_error()

        if rails_e is not None:
            logger.warning("Page was blocked by rails error, renavigating.")
            logger.error(rails_e)
            # RHEL7 top does not know -M and -a
            logger.debug('Top CPU consumers:')
            logger.debug(store.current_appliance.ssh_client.run_command(
                'top -c -b -n1 | head -30').output)
            logger.debug('Top Memory consumers:')
            logger.debug(store.current_appliance.ssh_client.run_command(
                'top -c -b -n1 -o "%MEM" | head -30').output)  # noqa
            logger.debug('Managed known Providers:')
            logger.debug(
                '%r', [prov.key for prov in store.current_appliance.managed_known_providers])
            self.appliance.browser.quit_browser()
            self.appliance.browser.open_browser()
            self.go(_tries, *args, **go_kwargs)
            # If there is a rails error past this point, something is really awful

        # Set this to True in the handlers below to trigger a browser restart
        recycle = False

        # Set this to True in handlers to restart evmserverd on the appliance
        # Includes recycling so you don't need to specify recycle = False
        restart_evmserverd = False

        try:
            self.log_message(
                "Invoking {}, with {} and {}".format(fn.func_name, args, kwargs), level="debug")
            return fn(*args, **kwargs)
        except (KeyboardInterrupt, ValueError):
            # KeyboardInterrupt: Don't block this while navigating
            raise
        except UnexpectedAlertPresentException:
            if _tries == 1:
                # There was an alert, accept it and try again
                br.widgetastic.handle_alert(wait=0)
                self.go(_tries, *args, **go_kwargs)
            else:
                # There was still an alert when we tried again, shoot the browser in the head
                logger.debug('Unxpected alert, recycling browser')
                recycle = True
        except (ErrorInResponseException, InvalidSwitchToTargetException):
            # Unable to switch to the browser at all, need to recycle
            logger.info('Invalid browser state, recycling browser')
            recycle = True
        except exceptions.CFMEExceptionOccured as e:
            # We hit a Rails exception
            logger.info('CFME Exception occured')
            logger.exception(e)
            recycle = True
        except exceptions.CannotContinueWithNavigation as e:
            # The some of the navigation steps cannot succeed
            logger.info('Cannot continue with navigation due to: {}; '
                'Recycling browser'.format(str(e)))
            recycle = True
        except (NoSuchElementException, InvalidElementStateException, WebDriverException,
                StaleElementReferenceException) as e:
            from cfme.web_ui import cfme_exception as cfme_exc  # To prevent circular imports
            # First check - if jquery is not found, there can be also another
            # reason why this happened so do not put the next branches in elif
            if isinstance(e, WebDriverException) and "jQuery" in str(e):
                # UI failed in some way, try recycling the browser
                logger.exception(
                    "UI failed in some way, jQuery not found, (probably) recycling the browser.")
                recycle = True
            # If the page is blocked, then recycle...
            # TODO .modal-backdrop.fade.in catches the 'About' modal resulting in nav loop
            if (
                    br.widgetastic.is_displayed("//div[@id='blocker_div' or @id='notification']") or
                    br.widgetastic.is_displayed(".modal-backdrop.fade.in")):
                logger.warning("Page was blocked with blocker div, recycling.")
                recycle = True
            elif cfme_exc.is_cfme_exception():
                logger.exception("CFME Exception before force navigate started!: {}".format(
                    cfme_exc.cfme_exception_text()))
                recycle = True
            elif br.widgetastic.is_displayed("//body/h1[normalize-space(.)='Proxy Error']"):
                # 502
                logger.exception("Proxy error detected. Killing browser and restarting evmserverd.")
                req = br.widgetastic.elements("/html/body/p[1]//a")
                req = br.widgetastic.text(req[0]) if req else "No request stated"
                reason = br.widgetastic.elements("/html/body/p[2]/strong")
                reason = br.widgetastic.text(reason[0]) if reason else "No reason stated"
                logger.info("Proxy error: {} / {}".format(req, reason))
                restart_evmserverd = True
            elif br.widgetastic.is_displayed("//body[./h1 and ./p and ./hr and ./address]"):
                # 503 and similar sort of errors
                title = br.widgetastic.text("//body/h1")
                body = br.widgetastic.text("//body/p")
                logger.exception("Application error {}: {}".format(title, body))
                sleep(5)  # Give it a little bit of rest
                recycle = True
            elif br.widgetastic.is_displayed("//body/div[@class='dialog' and ./h1 and ./p]"):
                # Rails exception detection
                logger.exception("Rails exception before force navigate started!: %r:%r at %r",
                    br.widgetastic.text("//body/div[@class='dialog']/h1"),
                    br.widgetastic.text("//body/div[@class='dialog']/p"),
                    getattr(manager.browser, 'current_url', "error://dead-browser")
                )
                recycle = True
            elif br.widgetastic.elements("//ul[@id='maintab']/li[@class='inactive']") and not\
                    br.widgetastic.elements("//ul[@id='maintab']/li[@class='active']/ul/li"):
                # If upstream and is the bottom part of menu is not displayed
                logger.exception("Detected glitch from BZ#1112574. HEADSHOT!")
                recycle = True
            elif not self.obj.appliance.server.logged_in():
                # Session timeout or whatever like that, login screen appears.
                logger.exception("Looks like we are logged out. Try again.")
                recycle = True
            else:
                logger.error("Could not determine the reason for failing the navigation. " +
                    " Reraising.  Exception: {}".format(str(e)))
                logger.debug(store.current_appliance.ssh_client.run_command(
                    'systemctl status evmserverd').output)
                raise

        if restart_evmserverd:
            logger.info("evmserverd restart requested")
            self.appliance.restart_evm_service()
            self.appliance.wait_for_web_ui()
            self.go(_tries, *args, **go_kwargs)

        if recycle or restart_evmserverd:
            self.appliance.browser.quit_browser()
            logger.debug('browser killed on try {}'.format(_tries))
            # If given a "start" nav destination, it won't be valid after quitting the browser
            self.go(_tries, *args, **go_kwargs)

    @can_skip_badness_test
    def resetter(self, *args, **kwargs):
        pass

    @can_skip_badness_test
    def pre_navigate(self, *args, **kwargs):
        pass

    @can_skip_badness_test
    def post_navigate(self, *args, **kwargs):
        pass

    def log_message(self, msg, level="debug"):
        class_name = self.obj.__name__ if isclass(self.obj) else self.obj.__class__.__name__
        str_msg = "[UI-NAV/{}/{}]: {}".format(class_name, self._name, msg)
        getattr(logger, level)(str_msg)

    def construst_message(self, here, resetter, view, duration):
        str_here = "Already Here" if here else "Needed Navigation"
        str_resetter = "Resetter Used" if resetter else "No Resetter"
        str_view = "View Returned" if view else "No View Available"
        return "{}/{}/{} (elapsed {}ms)".format(str_here, str_resetter, str_view, duration)

    def go(self, _tries=0, *args, **kwargs):
        nav_args = {'use_resetter': True}
        self.log_message("Beginning Navigation...", level="info")
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
        self.check_for_badness(self.pre_navigate, _tries, nav_args, *args, **kwargs)
        here = False
        resetter_used = False
        try:
            here = self.check_for_badness(self.am_i_here, _tries, nav_args, *args, **kwargs)
        except Exception as e:
            self.log_message(
                "Exception raised [{}] whilst checking if already here".format(e), level="error")
        if not here:
            self.log_message("Prerequiesite Needed")
            self.prerequisite_view = self.prerequisite()
            self.check_for_badness(self.step, _tries, nav_args, *args, **kwargs)
        if nav_args['use_resetter']:
            resetter_used = True
            self.check_for_badness(self.resetter, _tries, nav_args, *args, **kwargs)
        self.check_for_badness(self.post_navigate, _tries, nav_args, *args, **kwargs)
        view = self.view if self.VIEW is not None else None
        duration = int((time.time() - start_time) * 1000)
        self.log_message(self.construst_message(here, resetter_used, view, duration), level="info")
        return view


navigator = Navigate()
navigate_to = navigator.navigate


class ViaUI(Implementation):
    """UI implementation using the normal ux"""

    def __str__(self):
        return 'UI'

    @cached_property
    def widgetastic(self):
        """This gives us a widgetastic browser."""
        browser = self.open_browser(url_key=self.appliance.server.address())
        wt = MiqBrowser(browser, self)
        manager.add_cleanup(self._reset_cache)
        return wt
