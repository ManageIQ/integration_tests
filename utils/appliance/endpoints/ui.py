from utils.log import logger
from cfme import exceptions
from cfme.fixtures.pytest_selenium import (
    is_displayed, ContextWrapper, execute_script, click,
    get_rails_error, handle_alert, elements, text)
from time import sleep

from navmazing import Navigate, NavigateStep
from selenium.common.exceptions import (
    ErrorInResponseException, InvalidSwitchToTargetException,
    InvalidElementStateException, WebDriverException, UnexpectedAlertPresentException,
    NoSuchElementException, StaleElementReferenceException)
from utils.browser import quit, ensure_browser_open, browser
from fixtures.pytest_store import store
from cfme.web_ui.menu import Menu


class ViaUI(object):
    """UI implementation using the normal ux"""
    # ** Wow, a lot to talk about here. so we introduced the idea of this "endpoint" object at
    # ** the moment. This endpoint object contains everything you need to talk to that endpoint.
    # ** Sessions, endpoint sepcific functions(a la force navigate). The base class does precious
    # ** little. It's more an organizational level thing.
    def __init__(self, owner):
        self.owner = owner
        self.menu = Menu()

    # ** Notice our friend force_navigate is here. It used to live in pytest_selenium fixture.
    # ** Funny story! That thing was never a fixture.
    # ** Now it lives here, because it is an implementation/endpoint specific function.
    # ** Almost all of our sel functions, click, move_to_element, elements, etc, will move here.
    # ** This is what this module is for. It's for describing the way we interact with the endpoint.
    def force_navigate(self, page_name, _tries=0, *args, **kwargs):
        """force_navigate(page_name)

        Given a page name, attempt to navigate to that page no matter what breaks.

        Args:
            page_name: Name a page from the current :py:data:`ui_navigate.nav_tree`
            tree to navigate to.

        """
        if _tries > 2:
            # Need at least three tries:
            # 1: login_admin handles an alert or CannotContinueWithNavigation appears.
            # 2: Everything should work. If not, NavigationError.
            raise exceptions.NavigationError(page_name)

        if "context" in kwargs:
            if not isinstance(kwargs["context"], ContextWrapper) and isinstance(
                    kwargs["context"], dict):
                kwargs["context"] = ContextWrapper(kwargs["context"])

        _tries += 1

        logger.debug('force_navigate to {}, try {}'.format(page_name, _tries))
        # circular import prevention: cfme.login uses functions in this module
        from cfme import login
        # Import the top-level nav menus for convenience

        # ** Notice here that the menu is an attribute of the endpoint because it too is endpoint
        # ** specific. Menu is not something global anymore, we don't need a Menu for REST,
        # ** therefore we don't need a Menu object globally, or in the REST module.
        # Collapse the stack
        self.menu.initialize()

        # browser fixture should do this, but it's needed for subsequent calls
        ensure_browser_open()

        # check for MiqQE javascript patch in 5.6 on first try and patch the appliance if necessary
        # raise an exception on subsequent unsuccessful attempts to access the MiqQE
        # javascript funcs
        if self.owner.version >= "5.5.5.0":
            def _patch_recycle_retry():
                self.owner.patch_with_miqqe()
                browser().quit()
                # ** There are a few of these, force_navigates that now reference themselves.
                self.force_navigate(page_name, _tries, *args, **kwargs)
            try:
                # latest js diff version always has to be placed here to keep this check current
                ver = execute_script("return MiqQE_version")
                if ver < 2:
                    logger.info("Old patch present on appliance; patching appliance")
                    _patch_recycle_retry()
            except WebDriverException as ex:
                if 'is not defined' in str(ex):
                    if _tries == 1:
                        logger.info("MiqQE javascript not defined; patching appliance")
                        _patch_recycle_retry()
                    else:
                        raise exceptions.CFMEException(
                            "Unable to navigate, patching the appliance's javascript"
                            "failed: {}".format(
                                str(ex)))
                else:
                    raise

        # Clear any running "spinnies"
        try:
            execute_script('miqSparkleOff();')
        except:  # Diaper OK (mfalesni)
            # miqSparkleOff undefined, so it's definitely off.
            pass

        # Set this to True in the handlers below to trigger a browser restart
        recycle = False

        # Set this to True in handlers to restart evmserverd on the appliance
        # Includes recycling so you don't need to specify recycle = False
        restart_evmserverd = False

        # remember the current user, if any
        current_user = store.user

        # Check if the page is blocked with blocker_div. If yes, let's headshot the
        # browser right here
        if (
                is_displayed("//div[@id='blocker_div' or @id='notification']", _no_deeper=True)
                or is_displayed(".modal-backdrop.fade.in", _no_deeper=True)):
            logger.warning("Page was blocked with blocker div on start of navigation, recycling.")
            quit()
            kwargs.pop("start", None)
            self.force_navigate("dashboard")  # Start fresh

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
            with self.ssh_client as ssh:
                # Blow off the Vim brokers and UI workers
                ssh.run_rails_command("\"(MiqVimBrokerWorker.all + MiqUiWorker.all).each &:kill\"")
            logger.info("Waiting for web UI to come back alive.")
            sleep(10)   # Give it some rest
            self.owner.wait_for_web_ui()
            quit()
            ensure_browser_open()
            kwargs.pop("start", None)
            self.force_navigate("dashboard")  # And start fresh

        # Same with rails errors
        rails_e = get_rails_error()
        if rails_e is not None:
            logger.warning("Page was blocked by rails error, renavigating.")
            logger.error(rails_e)
            if self.version < "5.5":
                logger.debug('Top CPU consumers:')
                logger.debug(self.owner.ssh_client.run_command(
                    'top -c -b -n1 -M | head -30').output)
                logger.debug('Top Memory consumers:')
                logger.debug(self.owner.ssh_client.run_command(
                    'top -c -b -n1 -M -a | head -30').output)
            else:
                # RHEL7 top does not know -M and -a
                logger.debug('Top CPU consumers:')
                logger.debug(self.owner.ssh_client.run_command(
                    'top -c -b -n1 | head -30').output)
                logger.debug('Top Memory consumers:')
                logger.debug(self.owner.ssh_client.run_command(
                    'top -c -b -n1 -o "%MEM" | head -30').output)  # noqa
            logger.debug('Managed Providers:')
            logger.debug(self.owner.managed_providers)
            quit()  # Refresh the session, forget loaded summaries, ...
            kwargs.pop("start", None)
            ensure_browser_open()
            self.menu.go_to("dashboard")
            # If there is a rails error past this point, something is really awful

        def _login_func():
            if not current_user:  # default to admin user
                login.login_admin()
            else:  # we recycled and want to log back in
                login.login(store.user)

        try:
            try:
                # What we'd like to happen...
                _login_func()
            except WebDriverException as e:
                if "jquery" not in str(e).lower():
                    raise  # Something unknown happened
                logger.info("Seems we got a non-CFME page (blank or screwed up)"
                    "so killing the browser")
                quit()
                ensure_browser_open()
                # And try it again
                _login_func()
                # If this failed, no help with that :/

            ctx = kwargs.get("context", False)
            if ctx:
                logger.info('Navigating to %s with context: %s', page_name, ctx)
            else:
                logger.info('Navigating to %s', page_name)
            self.menu.go_to(page_name, *args, **kwargs)
        except (KeyboardInterrupt, ValueError):
            # KeyboardInterrupt: Don't block this while navigating
            # ValueError: ui_navigate.go_to can't handle this page, give up
            raise
        except UnexpectedAlertPresentException:
            if _tries == 1:
                # There was an alert, accept it and try again
                handle_alert(wait=0)
                self.force_navigate(page_name, _tries, *args, **kwargs)
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
            logger.info('Cannot continue with navigation due to: {}; Recycling browser'.format(
                str(e)))
            recycle = True
        except (NoSuchElementException, InvalidElementStateException, WebDriverException,
                StaleElementReferenceException) as e:
            from cfme.web_ui import cfme_exception as cfme_exc  # To prevent circular imports
            # First check - if jquery is not found, there can be also another
            # reason why this happened
            # so do not put the next branches in elif
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
                logger.exception("CFME Exception before force_navigate started!: `%s`",
                    cfme_exc.cfme_exception_text())
                recycle = True
            elif is_displayed("//body/h1[normalize-space(.)='Proxy Error']"):
                # 502
                logger.exception("Proxy error detected. Killing browser and restarting evmserverd.")
                req = elements("/html/body/p[1]//a")
                req = text(req[0]) if req else "No request stated"
                reason = elements("/html/body/p[2]/strong")
                reason = text(reason[0]) if reason else "No reason stated"
                logger.info("Proxy error: %s / %s", req, reason)
                restart_evmserverd = True
            elif is_displayed("//body[./h1 and ./p and ./hr and ./address]", _no_deeper=True):
                # 503 and similar sort of errors
                title = text("//body/h1")
                body = text("//body/p")
                logger.exception("Application error %s: %s", title, body)
                sleep(5)  # Give it a little bit of rest
                recycle = True
            elif is_displayed("//body/div[@class='dialog' and ./h1 and ./p]", _no_deeper=True):
                # Rails exception detection
                logger.exception("Rails exception before force_navigate started!: %s:%s at %s",
                    text("//body/div[@class='dialog']/h1").encode("utf-8"),
                    text("//body/div[@class='dialog']/p").encode("utf-8"),
                    # ** This call will eventually access the browser from this very object,
                    # ** self.browser or something something.
                    browser().current_url()
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
                    " Reraising.  Exception: %s", str(e))
                logger.debug(self.owner.ssh_client.run_command(
                    'service evmserverd status').output)
                raise

        if restart_evmserverd:
            logger.info("evmserverd restart requested")
            self.owner.restart_evm_service()
            self.owner.wait_for_web_ui()

        if recycle or restart_evmserverd:
            browser().quit()  # login.current_user() will be retained for next login
            logger.debug('browser killed on try %d', _tries)
            # If given a "start" nav destination, it won't be valid after quitting the browser
            kwargs.pop("start", None)
            self.force_navigate(page_name, _tries, *args, **kwargs)


class CFMENavigateStep(NavigateStep):
    def pre_navigate(self, _tries=0):
        if _tries > 2:
            # Need at least three tries:
            # 1: login_admin handles an alert or CannotContinueWithNavigation appears.
            # 2: Everything should work. If not, NavigationError.
            raise exceptions.NavigationError(self.obj._name)

        ensure_browser_open()

        def _patch_recycle_retry():
            store.current_appliance.patch_with_miqqe()
            browser().quit()
            self.go(_tries)
        try:
            # latest js diff version always has to be placed here to keep this check current
            ver = execute_script("return MiqQE_version")
            if ver < 2:
                logger.info("Old patch present on appliance; patching appliance")
                _patch_recycle_retry()
        except WebDriverException as ex:
            if 'is not defined' in str(ex):
                if _tries == 1:
                    logger.info("MiqQE javascript not defined; patching appliance")
                    _patch_recycle_retry()
                else:
                    raise exceptions.CFMEException(
                        "Unable to navigate, patching the appliance's javascript failed: {}".format(
                            str(ex)))
            else:
                raise
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
            quit()
            ensure_browser_open()
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
            quit()  # Refresh the session, forget loaded summaries, ...
            ensure_browser_open()
            self.go(_tries)
            # If there is a rails error past this point, something is really awful

    def do_nav(self, _tries=0):
        # Set this to True in the handlers below to trigger a browser restart
        recycle = False

        # Set this to True in handlers to restart evmserverd on the appliance
        # Includes recycling so you don't need to specify recycle = False
        restart_evmserverd = False

        current_user = store.user
        from cfme import login

        def _login_func():
            if not current_user:  # default to admin user
                login.login_admin()
            else:  # we recycled and want to log back in
                login.login(store.user)

        try:
            try:
                # What we'd like to happen...
                _login_func()
            except WebDriverException as e:
                if "jquery" not in str(e).lower():
                    raise  # Something unknown happened
                logger.info("Seems we got a non-CFME page (blank "
                    "or screwed up) so killing the browser")
                quit()
                ensure_browser_open()
                # And try it again
                _login_func()
                # If this failed, no help with that :/

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
                    browser().current_url
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
            browser().quit()  # login.current_user() will be retained for next login
            logger.debug('browser killed on try {}'.format(_tries))
            # If given a "start" nav destination, it won't be valid after quitting the browser
            self.go(_tries)

    def go(self, _tries=0):
        _tries += 1
        self.pre_navigate(_tries)
        logger.debug("NAVIGATE: Checking if already at {}".format(self._name))
        try:
            if self.am_i_here():
                logger.debug("NAVIGATE: Already at {}".format(self._name))
                return
        except Exception as e:
            logger.debug("NAVIGATE: Exception raised [{}] whilst checking if already at {}".format(
                e, self._name))
        logger.debug("NAVIGATE: I'm not at {}".format(self._name))
        self.prerequisite()
        logger.debug("NAVIGATE: Heading to destination {}".format(self._name))
        self.do_nav(_tries)
        self.post_navigate(_tries)

navigate = Navigate()
