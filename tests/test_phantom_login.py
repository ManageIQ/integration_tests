from unittestzero import Assert

from pages.login import LoginPage
from utils.browser import testsetup


def test_phantom_login(browser):
    """https://bugzilla.redhat.com/show_bug.cgi?id=996284"""
    login_pg = LoginPage(testsetup)
    login_pg.go_to_login_page()
    next_pg = login_pg.login_and_send_window_size()
    Assert.not_equal(next_pg.get_context_current_page(), '/',
        "Phantom Login - Got redirected back to the login page after logging in")
