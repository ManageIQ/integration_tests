"""Provides functions to login as any user

Also provides a convenience function for logging in as admin using
the credentials in the cfme yamls.

:var page: A :py:class:`cfme.web_ui.Region` holding locators on the login page
"""
from __future__ import absolute_import

from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, ElementNotVisibleException

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
from cfme import dashboard, Credential
from cfme.configure.access_control import User
from cfme.web_ui import Region, Form, fill, Input
from utils import conf, version
from utils.browser import ensure_browser_open, quit
from utils.log import logger
from fixtures.pytest_store import store


page = Region(
    title={version.LOWEST: "Dashboard", version.LATEST: "Login"},
    locators={
        'username': Input("user_name"),
        'password': Input("user_password"),
        'submit_button': '//a[@id="login"]|//button[normalize-space(.)="Login"]/..',
        # Login page has an abnormal flash div
        'flash': '//div[@id="flash_div"]',
        'logout': '//a[contains(@href, "/logout")]',
        'update_password': '//a[@title="Update Password"]',
        'back': '//a[@title="Back"]',
        'user_new_password': Input("user_new_password"),
        'user_verify_password': Input("user_verify_password")
    },
    identifying_loc='submit_button')

_form_fields = ('username', 'password', 'user_new_password', 'user_verify_password')
form = Form(
    fields=[
        loc for loc
        in page.locators.items()
        if loc[0] in _form_fields],
    identifying_loc='username')


def click_on_login():
    """
    Convenience internal function to click the login locator submit button.
    """
    sel.click(page.submit_button)


def _js_auth_fn():
    # In case clicking on login or hitting enter is broken, this can still let you log in
    # This shouldn't be used in automation, though.
    sel.execute_script('miqAjaxAuth();')


def logged_in():
    ensure_browser_open()
    with sel.ajax_timeout(90):
        sel.wait_for_ajax()  # This is called almost everywhere, protects from spinner
    return sel.is_displayed(dashboard.page.user_dropdown)


def press_enter_after_password():
    """
    Convenience function to send a carriange return at the end of the password field.
    """
    sel.send_keys(page.password, Keys.RETURN)


LOGIN_METHODS = [click_on_login, press_enter_after_password]


def login(user, submit_method=_js_auth_fn):
    """
    Login to CFME with the given username and password.
    Optionally, submit_method can be press_enter_after_password
    to use the enter key to login, rather than clicking the button.

    Args:
        user: The username to fill in the username field.
        password: The password to fill in the password field.
        submit_method: A function to call after the username and password have been input.

    Raises:
        RuntimeError: If the login fails, ie. if a flash message appears
    """

    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = User(credential=cred)

    if not logged_in() or user.credential.principal is not current_username():
        if logged_in():
            logout()
        # workaround for strange bug where we are logged out
        # as soon as we click something on the dashboard
        sel.sleep(1.0)

        logger.debug('Logging in as user %s' % user.credential.principal)
        try:
            fill(form, {'username': user.credential.principal, 'password': user.credential.secret})
        except sel.InvalidElementStateException as e:
            logger.warning("Got an error. Details follow.")
            msg = str(e).lower()
            if "element is read-only" in msg:
                logger.warning("Got a read-only login form, will reload the browser.")
                # Reload browser
                quit()
                ensure_browser_open()
                sel.sleep(1.0)
                sel.wait_for_ajax()
                # And try filling the form again
                fill(form, {'username': user.credential.principal,
                    'password': user.credential.secret})
            else:
                logger.warning("Unknown error, reraising.")
                logger.exception(e)
                raise
        with sel.ajax_timeout(90):
            submit_method()
        flash.assert_no_errors()
        user.full_name = _full_name()
        store.user = user


def login_admin(**kwargs):
    """
    Convenience function to log into CFME using the admin credentials from the yamls.

    Args:
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.
    """
    if current_full_name() != 'Administrator':
        logout()

        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = User(credential=cred)
        login(user, **kwargs)


def logout():
    """
    Logs out of CFME.
    """
    if logged_in():
        if not sel.is_displayed(page.logout):
            sel.click(dashboard.page.user_dropdown)
        sel.click(page.logout, wait_ajax=False)
        sel.handle_alert(wait=False)
        store.user = None


def _full_name():
    return sel.text(dashboard.page.user_dropdown).split('|')[0].strip()


def current_full_name():
    """ Returns the current username.

    Returns: the current username.
    """
    if logged_in():
        return _full_name()
    else:
        return None


def current_user():
    return store.user


def current_username():
    u = current_user()
    return u and u.credential.principal


def fill_login_fields(username, password):
    """ Fills in login information without submitting the form """
    if logged_in():
        logout()
    fill(form, {"username": username, "password": password})


def show_password_update_form():
    """ Shows the password update form """
    if logged_in():
        logout()
    try:
        sel.click(page.update_password)
    except ElementNotVisibleException:
        # Already on password change form
        pass


def update_password(username, password, new_password,
                    verify_password=None, submit_method=click_on_login):
    """ Changes user password """
    if logged_in():
        logout()
    show_password_update_form()
    fill(form, {
        "username": username,
        "password": password,
        "user_new_password": new_password,
        "user_verify_password": verify_password if verify_password is not None else new_password
    })
    submit_method()


def close_password_update_form():
    """ Goes back to main login form on login page """
    try:
        sel.click(page.back)
    except (ElementNotVisibleException, NoSuchElementException):
        # Already on main login form or not on login page at all
        pass


def clear_fields():
    """ clears all form fields """
    fill(form, {
        "username": "",
        "password": "",
        "user_new_password": "",
        "user_verify_password": ""
    })
