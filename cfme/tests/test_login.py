import pytest
from cfme import dashboard, login, Credential
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


@pytest.mark.sauce
@pytest.mark.smoke
@pytest.mark.parametrize(
    "method", login.LOGIN_METHODS, ids=[x.__name__ for x in login.LOGIN_METHODS])
@pytest.mark.usefixtures("check_logged_out")
def test_login(method):
    """ Tests that the appliance can be logged into and shows dashboard page. """
    pytest.sel.get(pytest.sel.base_url())
    assert not pytest.sel.is_displayed(dashboard.page.user_dropdown)
    login.login_admin(submit_method=method)
    assert pytest.sel.is_displayed(dashboard.page.user_dropdown), "Could not determine if logged in"
    login.logout()
    assert login.page.is_displayed()


@pytest.mark.sauce
def test_bad_password():
    """ Tests logging in with a bad password. """
    pytest.sel.get(pytest.sel.base_url())
    creds = Credential(principal=conf.credentials['default']['username'], secret="badpassword@#$")
    user = User(credential=creds)

    with error.expected('Sorry, the username or password you entered is incorrect.'):
        login.login(user)
        assert login.page.is_displayed()
