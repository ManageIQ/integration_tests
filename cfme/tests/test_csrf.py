# -*- coding: utf-8 -*-
import pytest

from cfme.base.ui import Server, LoginPage
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for, TimedOutError


@pytest.mark.tier(2)
def test_csrf_post(appliance):
    """CSRF should prevent forged POST requests

    POST requests use the CSRF token to validate requests, so setting the token
    to something invalid should set off the CSRF detector and reject the request

    """
    dashboard = navigate_to(Server, 'Dashboard')
    dashboard.csrf_token = "Bogus!"
    dashboard.reset_widgets(cancel=False)

    login_page = appliance.browser.create_view(LoginPage)

    try:
        wait_for(lambda: login_page.is_displayed, num_sec=15, delay=0.2)
    except TimedOutError:
        pytest.fail("CSRF attack succeeded!")
