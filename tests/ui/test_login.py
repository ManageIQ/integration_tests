from unittestzero import Assert
from pages.login import LoginPage

from utils.browser import testsetup


class TestLogin:
    def test_login(self, browser):
        login_pg = LoginPage(testsetup)
        login_pg.go_to_login_page()
        home_pg = login_pg.login()
        Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
