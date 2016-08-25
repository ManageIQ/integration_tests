import pytest
from cfme import login, Credential
from cfme import BasicLoggedInView
from cfme.login import LoginPage
from cfme.configure.access_control import User
from utils import browser, conf, error

pytestmark = pytest.mark.usefixtures('browser')


@pytest.yield_fixture(scope="function")
def check_logged_out():
    if browser.browser() is not None:
        browser.quit()
        browser.ensure_browser_open()
        login.logout()
    yield
    if browser.browser() is not None:
        browser.quit()
        browser.ensure_browser_open()
        login.logout()


@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.smoke
@pytest.mark.parametrize(
    "method", login.LOGIN_METHODS, ids=[x.__name__ for x in login.LOGIN_METHODS])
@pytest.mark.usefixtures("check_logged_out")
def test_login(method, open_view):
    """ Tests that the appliance can be logged into and shows dashboard page. """
    pytest.sel.get(pytest.sel.base_url())
    logged_in = open_view(BasicLoggedInView, navigate=False)
    assert not logged_in.is_displayed
    login.login_admin(submit_method=method)
    assert logged_in.is_displayed
    login.logout()
    login_page = open_view(LoginPage, navigate=False)
    assert login_page.is_displayed


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_bad_password(open_view):
    """ Tests logging in with a bad password. """
    pytest.sel.get(pytest.sel.base_url())
    creds = Credential(principal=conf.credentials['default']['username'], secret="badpassword@#$")
    user = User(credential=creds)

    with error.expected("Sorry, the username or password you entered is incorrect."):
        login.login(user)
        login_page = open_view(LoginPage, navigate=False)
        assert login_page.is_displayed
