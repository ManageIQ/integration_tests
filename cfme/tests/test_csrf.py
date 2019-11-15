import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [test_requirements.general_ui]


@pytest.mark.tier(2)
def test_csrf_post(appliance):
    """CSRF should prevent forged POST requests

    POST requests use the CSRF token to validate requests, so setting the token
    to something invalid should set off the CSRF detector and reject the request


    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    dashboard = navigate_to(appliance.server, 'Dashboard')
    dashboard.csrf_token = "Bogus!"
    dashboard.reset_widgets(cancel=False)

    try:
        wait_for(
            lambda: dashboard.logged_out, num_sec=15, delay=0.2)
    except TimedOutError:
        pytest.fail("CSRF attack succeeded!")
