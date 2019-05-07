import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [test_requirements.rest, pytest.mark.tier(1)]


def test_update_advanced_settings_new_key(appliance, request):
    """
    This test case checks updating advanced settings with a new key-value pair
    and tests that this change does not break the Configuration page

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h

    Bugzilla:
        1695566
    """
    data = {"new_key": "new value"}
    appliance.update_advanced_settings(data)

    @request.addfinalizer
    def _reset_settings():
        data["new_key"] = "<<reset>>"
        appliance.update_advanced_settings(data)

    assert "new_key" in appliance.advanced_settings

    view = navigate_to(appliance.server, "Advanced")
    assert view.is_displayed
