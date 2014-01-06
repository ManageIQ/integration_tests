import pytest
from unittestzero import Assert
from cfme.login import login_admin, login
import cfme.dashboard as dashboard
from utils import conf


@pytest.mark.usefixtures("browser")
def test_login():
    login_admin()
    Assert.true(dashboard.page.is_displayed(), "Could not determine if logged in")


def test_bad_password():
    try:
        login(conf.credentials['default']['username'], "badpassword@#$")
    except:
        pass
