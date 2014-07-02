import pytest
import cfme.login as login
from cfme import dashboard
from utils import conf, error

pytestmark = pytest.mark.usefixtures('browser')


@pytest.mark.smoke
def test_login():
    """ Tests that the appliance can be logged into and shows dashboard page. """
    pytest.sel.get(pytest.sel.base_url())
    login.login_admin()
    assert dashboard.page.is_displayed(), "Could not determine if logged in"
    login.logout()
    assert login.page.is_displayed()


def test_bad_password():
    """ Tests logging in with a bad password. """
    pytest.sel.get(pytest.sel.base_url())
    with error.expected('Sorry, the username or password you entered is incorrect.'):
        login.login(conf.credentials['default']['username'], "badpassword@#$")
    assert login.page.is_displayed()

@pytest.sel.go_to('dashboard')
def test_logout(logged_in):
    """ Tests that the provider can be logged out of. """
    login.logout()
    assert login.page.is_displayed()


def test_verify_password_update(request):
    """
    Tests that password changes are successful

    Warning: This will temporarily change the password for the default account.
    If you stop the tests unexpectedly, the password may not be reset to the default,
    making future logins based on the defaults unsuccessful until a manual reset of the
    password is done.

    If you need to manually reset the password, the current password should be the value
    of either new_password, username, or username + new_password.
    """
    username = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    new_password = "ThisIsTheNewPassword"
    current_password = password

    # Check that original login credentials work
    login.login(username, current_password)
    assert login.logged_in(), "yaml credentials are incorrect!"

    # Reset password once this function stops
    def reset_password():
        login.update_password(username, current_password, password)
        assert login.logged_in(), "password reset failed"
        login.logout()
        login.login(username, password)
        assert login.logged_in(), "password reset failed"
        login.logout()

    request.addfinalizer(reset_password)

    # Simple update
    login.update_password(username, current_password, new_password)
    assert login.logged_in()
    current_password = new_password

    # Username as password
    login.update_password(username, current_password, username)
    assert login.logged_in()
    current_password = username

    # New password starts with old password
    login.update_password(username, current_password, current_password + new_password)
    assert login.logged_in()
    current_password = current_password + new_password


def test_verify_bad_password_update():
    """
    Tests that if any information on the password update form is incorrect that the system
    rejects the change attempt and does not update the login information
    """
    username = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    new_password = "NewPassword192838474ujrejfd"

    # Ensure original login credentials work
    login.login(username, password)
    assert login.logged_in(), "yaml credentials are incorrect!"

    # Incorrect original password
    login.update_password(username, password + "ThisPartIsWrong", new_password)
    assert login.flash.is_error(login.flash.get_messages()[0])

    # New passwords don't match
    login.update_password(username, password, new_password, new_password + "3xtraCharacters")
    assert login.flash.is_error(login.flash.get_messages()[0])

    # Empty new password field
    login.clear_fields()
    login.update_password(username, password, "", new_password)
    assert login.flash.is_error(login.flash.get_messages()[0])

    # Empty new password verification field
    login.clear_fields()
    login.update_password(username, password, new_password, "")
    assert login.flash.is_error(login.flash.get_messages()[0])

    # Reset password to same password
    login.clear_fields()
    login.update_password(username, password, password)
    assert login.flash.is_error(login.flash.get_messages()[0])

    # Ensure original password still works
    login.close_password_update_form()
    login.login(username, password)
    assert login.logged_in(), "Password has been changed!"
