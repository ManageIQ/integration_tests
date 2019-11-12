import pytest
from selenium.common.exceptions import NoSuchElementException

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [test_requirements.timelines]


@pytest.mark.tier(2)
def test_timelines_removed(appliance):
    """
    Test that Cloud Intel->Timelines have been removed in upstream and 5.11 builds.
    Designed to pass for CFME 5.10.

    Bugzilla:
        1672933

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/12h
        casecomponent: WebUI
        caseimportance: medium
    """
    if appliance.is_downstream and appliance.version < "5.11":
        navigate_to(appliance.server, "CloudIntelTimelines")
    else:
        with pytest.raises(NoSuchElementException):
            navigate_to(appliance.server, "CloudIntelTimelines")


@pytest.mark.tier(2)
def test_rss_removed(appliance):
    """
    Test that Cloud Intel->RSS has been removed in upstream and 5.11 builds.
    Designed to pass for CFME 5.10.

    Bugzilla:
        1672933

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/12h
        casecomponent: WebUI
        caseimportance: medium
    """
    if appliance.is_downstream and appliance.version < "5.11":
        navigate_to(appliance.server, "RSS")
    else:
        with pytest.raises(NoSuchElementException):
            navigate_to(appliance.server, "RSS")
