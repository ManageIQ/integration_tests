import pytest
from unittestzero import Assert
from cfme.login import login_admin, login
import cfme.dashboard as dashboard
from cfme.fixtures.configuration import conf


@pytest.mark.usefixtures("selenium")
def test_login():
    login_admin()
    Assert.true(dashboard.page.is_displayed(), "Could not determine if logged in")


def test_bad_password():
    try:
        login(conf.get_in('cmfe', 'admin_user'), "badpassword@#$")
    except:
        pass
