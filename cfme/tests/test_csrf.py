# -*- coding: utf-8 -*-
import pytest

from cfme.dashboard import Dashboard
from utils.wait import wait_for, TimedOutError


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[1285778, 'GH#ManageIQ/manageiq:5657'])
def test_csrf_post(create_view):
    """CSRF should prevent forged POST requests

    POST requests use the CSRF token to validate requests, so setting the token
    to something invalid should set off the CSRF detector and reject the request

    """
    dashboard = create_view(Dashboard)
    dashboard.csrf_token.fill("Bogus!")
    dashboard.reset_widgets()
    dashboard.browser.handle_alert(cancel=False)

    try:
        wait_for(lambda: dashboard.logged_out, num_sec=15, delay=0.2)
    except TimedOutError:
        rails_error = dashboard.browser.rails_error()
        if rails_error is None or 'InvalidAuthenticityToken' not in rails_error:
            pytest.fail("CSRF attack succeeded!")
