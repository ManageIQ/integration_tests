import pytest
from unittestzero import Assert

from pages.login import LoginPage

pytestmark = [pytest.mark.nondestructive]


def test_csrf_post(home_page_logged_in):
    """CSRF should prevent forged POST requests

    POST requests use the CSRF token to validate requests, so setting the token
    to something invalid should set off the CSRF detector and reject the request

    """

    home_pg = home_page_logged_in
    home_pg.csrf_token = 'Bogus!'
    home_pg.click_on_reset_widgets()

    # Bogus CSRF token should mean we get bounced back to the login page
    login_pg = LoginPage(home_pg.testsetup)
    login_pg._wait_for_visible_element(*login_pg._login_submit_button_locator)
    Assert.true(login_pg.is_the_current_page, 'CSRF Attack succeeded!')
