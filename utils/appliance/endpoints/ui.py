# -*- coding: utf-8 -*-
import json
import time
from jsmin import jsmin

from utils.log import logger, create_sublogger
from cfme import exceptions
from cfme.fixtures.pytest_selenium import (
    is_displayed, execute_script, click,
    get_rails_error, handle_alert, elements, text)
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
from werkzeug.local import LocalProxy
VersionPick.VERSION_CLASS = Version


class MiqBrowserPlugin(DefaultPlugin):
    ENSURE_PAGE_SAFE = jsmin('''\
        function isHidden(el) {if(el === null) return true; return el.offsetParent === null;}

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
            result = self.browser.execute_script(self.ENSURE_PAGE_SAFE)
            # TODO: Logging
            return bool(result)

        wait_for(_check, timeout=timeout, delay=0.2, silent_failure=True)

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
            interval += .1
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
    def __init__(self, endpoint, extra_objects=None):
        extra_objects = extra_objects or {}
        extra_objects.update({
            'appliance': endpoint.owner,
            'endpoint': endpoint,
            'store': store,
        })
        super(MiqBrowser, self).__init__(
            LocalProxy(manager.ensure_open),
            plugin_class=MiqBrowserPlugin,
            logger=create_sublogger('MiqBrowser'),
            extra_objects=extra_objects)

    @property
    def product_version(self):
        return self.extra_objects['appliance'].version


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

    def pre_navigate(self, _tries=0):
        if _tries > 2:
            # Need at least three tries:
            # 1: login_admin handles an alert or CannotContinueWithNavigation appears.
            # 2: Everything should work. If not, NavigationError.
            raise exceptions.NavigationError(self.obj._name)

        manager.ensure_open()

        # check for MiqQE javascript patch on first try and patch the appliance if necessary
        if store.current_appliance.is_miqqe_patch_candidate and \
                not store.current_appliance.miqqe_patch_applied:
            store.current_appliance.patch_with_miqqe()
            manager.quit()
            self.go(_tries)

        try:
            execute_script('miqSparkleOff();')
        except:  # Diaper OK (mfalesni)
            # miqSparkleOff undefined, so it's definitely off.
            pass

        # Check if the page is blocked with blocker_div. If yes, let's headshot the browser right
        # here
        if (
                is_displayed("//div[@id='blocker_div' or @id='notification']", _no_deeper=True)
                or is_displayed(".modal-backdrop.fade.in", _no_deeper=True)):
            logger.warning("Page was blocked with blocker div on start of navigation, recycling.")
            quit()
            self.go(_tries)

        # Check if modal window is displayed
        if (is_displayed(
                "//div[contains(@class, 'modal-dialog') and contains(@class, 'modal-lg')]",
                _no_deeper=True)):
            logger.warning("Modal window was open; closing the window")
            click("//button[contains(@class, 'close') and contains(@data-dismiss, 'modal')]")

        # Check if jQuery present
        try:
            execute_script("jQuery")
        except Exception as e:
            if "jQuery" not in str(e):
                logger.error("Checked for jQuery but got something different.")
                logger.exception(e)
            # Restart some workers
            logger.warning("Restarting UI and VimBroker workers!")
            with store.current_appliance.ssh_client as ssh:
                # Blow off the Vim brokers and UI workers
                ssh.run_rails_command("\"(MiqVimBrokerWorker.all + MiqUiWorker.all).each &:kill\"")
            logger.info("Waiting for web UI to come back alive.")
            sleep(10)   # Give it some rest
            store.current_appliance.wait_for_web_ui()
            manager.quit()
            manager.ensure_open()
            self.go(_tries)

        # Same with rails errors
        rails_e = get_rails_error()
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
            logger.debug('Managed Providers:')
            logger.debug(store.current_appliance.managed_providers)
            manager.quit()  # Refresh the session, forget loaded summaries, ...
            manager.ensure_open()
            self.go(_tries)
            # If there is a rails error past this point, something is really awful

    def do_nav(self, _tries=0):
        # Set this to True in the handlers below to trigger a browser restart
        recycle = False

        # Set this to True in handlers to restart evmserverd on the appliance
        # Includes recycling so you don't need to specify recycle = False
        restart_evmserverd = False

        from cfme import login

        try:
            self.step()
        except (KeyboardInterrupt, ValueError):
            # KeyboardInterrupt: Don't block this while navigating
            # ValueError: ui_navigate.go_to can't handle this page, give up
            raise
        except UnexpectedAlertPresentException:
            if _tries == 1:
                # There was an alert, accept it and try again
                handle_alert(wait=0)
                self.go(_tries)
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
            if (
                    is_displayed("//div[@id='blocker_div' or @id='notification']", _no_deeper=True)
                    or is_displayed(".modal-backdrop.fade.in", _no_deeper=True)):
                logger.warning("Page was blocked with blocker div, recycling.")
                recycle = True
            elif cfme_exc.is_cfme_exception():
                logger.exception("CFME Exception before force_navigate started!: {}".format(
                    cfme_exc.cfme_exception_text()))
                recycle = True
            elif is_displayed("//body/h1[normalize-space(.)='Proxy Error']"):
                # 502
                logger.exception("Proxy error detected. Killing browser and restarting evmserverd.")
                req = elements("/html/body/p[1]//a")
                req = text(req[0]) if req else "No request stated"
                reason = elements("/html/body/p[2]/strong")
                reason = text(reason[0]) if reason else "No reason stated"
                logger.info("Proxy error: {} / {}".format(req, reason))
                restart_evmserverd = True
            elif is_displayed("//body[./h1 and ./p and ./hr and ./address]", _no_deeper=True):
                # 503 and similar sort of errors
                title = text("//body/h1")
                body = text("//body/p")
                logger.exception("Application error {}: {}".format(title, body))
                sleep(5)  # Give it a little bit of rest
                recycle = True
            elif is_displayed("//body/div[@class='dialog' and ./h1 and ./p]", _no_deeper=True):
                # Rails exception detection
                logger.exception("Rails exception before force_navigate started!: %s:%s at %s",
                    text("//body/div[@class='dialog']/h1").encode("utf-8"),
                    text("//body/div[@class='dialog']/p").encode("utf-8"),
                    getattr(manager.browser, 'current_url', "error://dead-browser")
                )
                recycle = True
            elif elements("//ul[@id='maintab']/li[@class='inactive']") and not\
                    elements("//ul[@id='maintab']/li[@class='active']/ul/li"):
                # If upstream and is the bottom part of menu is not displayed
                logger.exception("Detected glitch from BZ#1112574. HEADSHOT!")
                recycle = True
            elif not login.logged_in():
                # Session timeout or whatever like that, login screen appears.
                logger.exception("Looks like we are logged out. Try again.")
                recycle = True
            else:
                logger.error("Could not determine the reason for failing the navigation. " +
                    " Reraising.  Exception: {}".format(str(e)))
                logger.debug(store.current_appliance.ssh_client.run_command(
                    'service evmserverd status').output)
                raise

        if restart_evmserverd:
            logger.info("evmserverd restart requested")
            store.current_appliance.restart_evm_service()
            store.current_appliance.wait_for_web_ui()

        if recycle or restart_evmserverd:
            manager.quit()  # login.current_user() will be retained for next login
            logger.debug('browser killed on try {}'.format(_tries))
            # If given a "start" nav destination, it won't be valid after quitting the browser
            self.go(_tries)

    def go(self, _tries=0):
        _tries += 1
        self.pre_navigate(_tries)
        self.appliance.browser.widgetastic.dismiss_any_alerts()
        logger.debug("NAVIGATE: Checking if already at {}".format(self._name))
        here = False
        try:
            here = self.am_i_here()
        except Exception as e:
            logger.debug("NAVIGATE: Exception raised [{}] whilst checking if already at {}".format(
                e, self._name))
        if here:
            logger.debug("NAVIGATE: Already at {}".format(self._name))
        else:
            logger.debug("NAVIGATE: I'm not at {}".format(self._name))
            self.prerequisite()
            logger.debug("NAVIGATE: Heading to destination {}".format(self._name))
            self.do_nav(_tries)
        self.resetter()
        self.post_navigate(_tries)
        if self.VIEW is not None:
            return self.view


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

    @cached_property
    def widgetastic(self):
        """This gives us a widgetastic browser."""
        return MiqBrowser(self)

    def create_view(self, view_class, additional_context=None):
        """Method that is used to instantiate a Widgetastic View.

        Views may define ``LOCATION`` on them, that implies a :py:meth:`force_navigate` call with
        ``LOCATION`` as parameter.

        Args:
            view_class: A view class, subclass of ``widgetastic.widget.View``
            additional_context: Additional informations passed to the view (user name, VM name, ...)
                which is also passed to the :py:meth:`force_navigate` in case when navigation is
                requested.

        Returns:
            An instance of the ``view_class``
        """
        additional_context = additional_context or {}
        view = view_class(
            self.widgetastic,
            additional_context=additional_context,
            logger=logger)

        return view
