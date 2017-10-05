# -*- coding: utf-8 -*-
import pytest

import time

from cfme.utils.browser import ensure_browser_open, quit
from cfme.utils.wait import wait_for

@pytest.mark.tier(3)
@pytest.mark.sauce
def test_session_timeout(request, appliance):
    """Sets the timeout to shortest possible time and waits if it really times out."""

    auth_settings = appliance.server.authentication
    @request.addfinalizer  # Wow, why we did not figure this out before?!
    def _finalize():
        quit()
        ensure_browser_open()
        auth_settings.set_session_timeout(hours="24", minutes="0")

    auth_settings.set_session_timeout(hours="0", minutes="5")
    # Wait 10 minutes
    time.sleep(10 * 60)
    # Try getting timeout
    # I had to use wait_for because on 5.4 and upstream builds it made weird errors
    wait_for(
        lambda: pytest.sel.elements(
            "//div[(@id='flash_div' or @id='login_div') and contains(normalize-space(.), "
            "'Session was timed out due to inactivity')]"),
        num_sec=60,
        delay=5,
        fail_func=lambda: pytest.sel.click("//a[normalize-space(text())='Cloud Intelligence']")
    )
