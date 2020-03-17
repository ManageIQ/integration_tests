import time

import pytest

from cfme import test_requirements
from cfme.utils.browser import manager
from cfme.utils.wait import wait_for


@pytest.mark.tier(3)
@test_requirements.configuration
@pytest.mark.sauce
def test_session_timeout(request, appliance):
    """Sets the timeout to shortest possible time and waits if it really times out.

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/8h
    """

    auth_settings = appliance.server.authentication

    @request.addfinalizer  # Wow, why we did not figure this out before?!
    def _finalize():
        manager.start()
        auth_settings.set_session_timeout(hours="24", minutes="0")

    auth_settings.set_session_timeout(hours="0", minutes="5")
    # Wait 10 minutes
    time.sleep(6 * 60)
    # Try getting timeout
    # I had to use wait_for because on 5.4 and upstream builds it made weird errors
    wait_for(
        lambda: appliance.browser.widgetastic.selenium.find_elements_by_xpath(
            "//div[(@id='flash_div' or @id='login_div') and contains(normalize-space(.), "
            "'Session was timed out due to inactivity')]"),
        num_sec=60,
        delay=5,
        fail_func=lambda: appliance.browser.widgetastic.selenium.click(
            "//a[normalize-space(text())='Cloud Intelligence']"
        )
    )


@test_requirements.rest
@pytest.mark.tier(0)
def test_bind_timeout_rest(appliance, request):
    """Sets the session timeout via REST

    Bugzilla:
        1553394

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
    """
    old_bind = appliance.advanced_settings.get('authentication', {}).get('bind_timeout')
    if not old_bind:
        pytest.skip('Unable to locate authentication:bind_timeout in advanced settings REST')
    request.addfinalizer(lambda: appliance.update_advanced_settings(
        {'authentication': {'bind_timeout': int(old_bind)}})
    )

    offset = int(old_bind) + 10
    appliance.update_advanced_settings({'authentication': {'bind_timeout': int(offset)}})
    assert int(appliance.advanced_settings['authentication']['bind_timeout']) == offset
