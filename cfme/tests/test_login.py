import pytest
from unittestzero import Assert
from cfme.login import login_admin, login, logout
from cfme.login import page as login_page
import cfme.dashboard as dashboard
from utils import conf

pytestmark = pytest.mark.usefixtures('browser')


def test_login():
    login_admin()
    Assert.true(dashboard.page.is_displayed(), "Could not determine if logged in")


def test_logout(logged_in):
    logout()
    #Assert.true(login_page.is_displayed())


def test_bad_password():
    try:
        login(conf.credentials['default']['username'], "badpassword@#$")
    except:
        pass
