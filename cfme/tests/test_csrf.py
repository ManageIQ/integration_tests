# -*- coding: utf-8 -*-
import pytest

from cfme import dashboard, login
from utils.wait import wait_for, TimedOutError


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[1285778, 'GH#ManageIQ/manageiq:5657'])
def test_csrf_post():
    """CSRF should prevent forged POST requests

    POST requests use the CSRF token to validate requests, so setting the token
    to something invalid should set off the CSRF detector and reject the request

    """
    pytest.sel.force_navigate("dashboard")
    dashboard.set_csrf_token("Bogus!")
    dashboard.reset_widgets()

    try:
        wait_for(lambda: login.page.is_displayed(), num_sec=15, delay=0.2)
    except TimedOutError:
        pytest.fail("CSRF attack succeeded!")
