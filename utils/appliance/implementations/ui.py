# -*- coding: utf-8 -*-
import json
import time
from jsmin import jsmin

from utils.log import StackedPrefixLoggerAdapter
from cfme import exceptions
from cfme.fixtures.pytest_selenium import get_rails_error
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
from widgetastic.utils import VersionPick
from utils.version import Version
from utils.wait import wait_for
VersionPick.VERSION_CLASS = Version


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
            logger=StackedPrefixLoggerAdapter(endpoint.owner.logger, {'item_type': 'BROWSER'}),
            extra_objects=extra_objects)

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


class StepLoggerAdapter(StackedPrefixLoggerAdapter):
    @property
    def prefix(self):
        return 'NAV/{}/{}'.format(self.extra['class_name'], self.extra['location_name'])


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

    @cached_property
    def logger(self):
        return StepLoggerAdapter(
            self.appliance.logger,
            {'class_name': type(self.obj).__name__, 'location_name': self._name})

    def create_view(self, *args, **kwargs):
        return self.appliance.browser.create_view(*args, **kwargs)

    def am_i_here(self):
        try:
            return self.view.is_displayed
        except (AttributeError, NoSuchElementException):
            return False

    def check_for_badness(self, fn, _tries, nav_args, *args, **kwargs):
        if getattr(fn, '_can_skip_badness_test', False):
            # self.logger.debug('Op is a Nop! ({})'.format(fn.__name__))
            return

        if self.VIEW:
            self.view.flush_widget_cache()
        go_kwargs = kwargs.copy()
        go_kwargs.update(nav_args)
        self.appliance.browser.open_browser()
        self.appliance.browser.widgetastic.dismiss_any_alerts()

        # check for MiqQE javascript patch on first try and patch the appliance if necessary
        if self.appliance.is_miqqe_patch_candidate and not self.appliance.miqqe_patch_applied:
            self.appliance.patch_with_miqqe()
            self.appliance.browser.quit_browser()
            _tries -= 1
            self.go(_tries, *args, **go_kwargs)

        br = self.appliance.browser

        try:
            br.widgetastic.execute_script('miqSparkleOff();', silent=True)
        except Exception:  # Diaper OK (mfalesni)
            # miqSparkleOff undefined, so it's definitely off.
            pass

        # Check if the page is blocked with blocker_div. If yes, let's headshot the browser right
        # here
        if (
                br.widgetastic.is_displayed("//div[@id='blocker_div' or @id='notification']") or
                br.widgetastic.is_displayed(".modal-backdrop.fade.in")):
            self.logger.warning(
                "Page was blocked with blocker div on start of navigation, recycling.")
            self.appliance.browser.quit_browser()
            self.go(_tries, *args, **go_kwargs)

        # Check if modal window is displayed
        if (br.widgetastic.is_displayed(
                "//div[contains(@class, 'modal-dialog') and contains(@class, 'modal-lg')]")):
            self.logger.warning("Modal window was open; closing the window")
            br.widgetastic.click(
                "//button[contains(@class, 'close') and contains(@data-dismiss, 'modal')]")

        # Check if jQuery present
        try:
            br.widgetastic.execute_script("jQuery", silent=True)
        except Exception as e:
            if "jQuery" not in str(e):
                self.logger.exception("Checked for jQuery but got something different.")
            # Restart some workers
            self.logger.warning("Restarting UI and VimBroker workers!")
            with self.appliance.ssh_client as ssh:
                # Blow off the Vim brokers and UI workers
                ssh.run_rails_command("\"(MiqVimBrokerWorker.all + MiqUiWorker.all).each &:kill\"")
            self.logger.info("Waiting for web UI to come back alive.")
            sleep(10)   # Give it some rest
            self.appliance.wait_for_web_ui()
            self.appliance.browser.quit_browser()
            self.appliance.browser.open_browser()
            self.go(_tries, *args, **go_kwargs)

        # Same with rails errors
        rails_e = get_rails_error()
        if rails_e is not None:
            self.logger.warning("Page was blocked by rails error, renavigating.")
            self.logger.error(rails_e)
            # RHEL7 top does not know -M and -a
            self.logger.debug('Top CPU consumers:')
            self.logger.debug(store.current_appliance.ssh_client.run_command(
                'top -c -b -n1 | head -30').output)
            self.logger.debug('Top Memory consumers:')
            self.logger.debug(store.current_appliance.ssh_client.run_command(
                'top -c -b -n1 -o "%MEM" | head -30').output)  # noqa
            self.logger.debug('Managed known Providers:')
            self.logger.debug(
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

        from cfme import login

        try:
            self.logger.debug("Invoking %s, with %r and %r", fn.func_name, args, kwargs)
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
                self.logger.debug('Unxpected alert, recycling browser')
                recycle = True
        except (ErrorInResponseException, InvalidSwitchToTargetException):
            # Unable to switch to the browser at all, need to recycle
            self.logger.info('Invalid browser state, recycling browser')
            recycle = True
        except exceptions.CFMEExceptionOccured as e:
            # We hit a Rails exception
            self.logger.exception('CFME Exception occured')
            recycle = True
        except exceptions.CannotContinueWithNavigation as e:
            # The some of the navigation steps cannot succeed
            self.logger.info('Cannot continue with navigation due to: %r; '
                'Recycling browser', e)
            recycle = True
        except (NoSuchElementException, InvalidElementStateException, WebDriverException,
                StaleElementReferenceException) as e:
            from cfme.web_ui import cfme_exception as cfme_exc  # To prevent circular imports
            # First check - if jquery is not found, there can be also another
            # reason why this happened so do not put the next branches in elif
            if isinstance(e, WebDriverException) and "jQuery" in str(e):
                # UI failed in some way, try recycling the browser
                self.logger.exception(
                    "UI failed in some way, jQuery not found, (probably) recycling the browser.")
                recycle = True
            # If the page is blocked, then recycle...
            if (
                    br.widgetastic.is_displayed("//div[@id='blocker_div' or @id='notification']") or
                    br.widgetastic.is_displayed(".modal-backdrop.fade.in")):
                self.logger.warning("Page was blocked with blocker div, recycling.")
                recycle = True
            elif cfme_exc.is_cfme_exception():
                self.logger.error("CFME Exception before force navigate started!: {}".format(
                    cfme_exc.cfme_exception_text()))
                recycle = True
            elif br.widgetastic.is_displayed("//body/h1[normalize-space(.)='Proxy Error']"):
                # 502
                self.logger.exception(
                    "Proxy error detected. Killing browser and restarting evmserverd.")
                req = br.widgetastic.elements("/html/body/p[1]//a")
                req = br.widgetastic.text(req[0]) if req else "No request stated"
                reason = br.widgetastic.elements("/html/body/p[2]/strong")
                reason = br.widgetastic.text(reason[0]) if reason else "No reason stated"
                self.logger.warning("Proxy error: {} / {}".format(req, reason))
                restart_evmserverd = True
            elif br.widgetastic.is_displayed("//body[./h1 and ./p and ./hr and ./address]"):
                # 503 and similar sort of errors
                title = br.widgetastic.text("//body/h1")
                body = br.widgetastic.text("//body/p")
                self.logger.error("Application error %s: %s", title, body)
                sleep(5)  # Give it a little bit of rest
                recycle = True
            elif br.widgetastic.is_displayed("//body/div[@class='dialog' and ./h1 and ./p]"):
                # Rails exception detection
                self.logger.exception("Rails exception before force navigate started!: %r:%r at %r",
                    br.widgetastic.text("//body/div[@class='dialog']/h1"),
                    br.widgetastic.text("//body/div[@class='dialog']/p"),
                    getattr(manager.browser, 'current_url', "error://dead-browser")
                )
                recycle = True
            elif br.widgetastic.elements("//ul[@id='maintab']/li[@class='inactive']") and not\
                    br.widgetastic.elements("//ul[@id='maintab']/li[@class='active']/ul/li"):
                # If upstream and is the bottom part of menu is not displayed
                self.logger.error("Detected glitch from BZ#1112574. HEADSHOT!")
                recycle = True
            elif not login.logged_in():
                # Session timeout or whatever like that, login screen appears.
                self.logger.error("Looks like we are logged out. Try again.")
                recycle = True
            else:
                self.logger.error("Could not determine the reason for failing the navigation. " +
                    " Reraising.  Exception: %s", e)
                self.logger.debug(store.current_appliance.ssh_client.run_command(
                    'systemctl evmserverd status').output)
                raise

        if restart_evmserverd:
            self.logger.info("evmserverd restart requested")
            self.appliance.restart_evm_service()
            self.appliance.wait_for_web_ui()
            self.go(_tries, *args, **go_kwargs)

        if recycle or restart_evmserverd:
            self.appliance.browser.quit_browser()
            self.logger.debug('browser killed on try {}'.format(_tries))
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

    def construct_message(self, here, resetter, view, duration):
        str_here = "Already Here" if here else "Needed Navigation"
        str_resetter = "Resetter Used" if resetter else "No Resetter"
        str_view = "View Returned" if view else "No View Available"
        return ("%s/%s/%s (elapsed %d ms)", str_here, str_resetter, str_view, duration)

    def go(self, _tries=0, *args, **kwargs):
        nav_args = {'use_resetter': True}
        self.logger.info("Beginning Navigation...")
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
        except Exception:
            self.log.exception(
                "Exception raised whilst checking if already here")
        if not here:
            self.logger.debug("Prerequisite Needed")
            self.prerequisite_view = self.prerequisite()
            self.check_for_badness(self.step, _tries, nav_args, *args, **kwargs)
        if nav_args['use_resetter']:
            resetter_used = True
            self.check_for_badness(self.resetter, _tries, nav_args, *args, **kwargs)
        self.check_for_badness(self.post_navigate, _tries, nav_args, *args, **kwargs)
        view = self.view if self.VIEW is not None else None
        duration = int((time.time() - start_time) * 1000)
        self.logger.info(*self.construct_message(here, resetter_used, view, duration))
        return view


navigator = Navigate()
navigate_to = navigator.navigate


class ViaUI(object):
    """UI implementation using the normal ux"""
    # ** Wow, a lot to talk about here. so we introduced the idea of this "endpoint" object at
    # ** the moment. This endpoint object contains everything you need to talk to that endpoint.
    # ** Sessions, endpoint sepcific functions(a la force navigate). The base class does precious
    # ** little. It's more an organizational level thing.
    def __init__(self, owner):
        self.owner = owner

    @property
    def appliance(self):
        return self.owner

    @cached_property
    def logger(self):
        return StackedPrefixLoggerAdapter(self.appliance.logger, {'item_type': 'WT'})

    @cached_property
    def widgetastic(self):
        """This gives us a widgetastic browser."""
        browser = self.open_browser()
        wt = MiqBrowser(browser, self)
        manager.add_cleanup(self._reset_cache)
        return wt

    def open_browser(self):
        # TODO: self.appliance.server.address() instead of None
        return manager.ensure_open(url_key=None)

    def quit_browser(self):
        manager.quit()

    def _reset_cache(self):
        try:
            del self.widgetastic
        except AttributeError:
            pass

    def create_view(self, view_class, additional_context=None):
        """Method that is used to instantiate a Widgetastic View.

        Args:
            view_class: A view class, subclass of ``widgetastic.widget.View``
            additional_context: Additional informations passed to the view (user name, VM name, ...)

        Returns:
            An instance of the ``view_class``
        """
        additional_context = additional_context or {}
        view = view_class(
            self.widgetastic,
            additional_context=additional_context,
            logger=self.logger)

        return view
