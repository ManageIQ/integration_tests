import pytest

from cfme import test_requirements
from cfme.configure import about

pytestmark = [test_requirements.general_ui]


@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1402112])
def test_about_region(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Open `About` modal and check the value of Region.

    Bugzilla:
        1402112
    """
    about_version = about.get_detail(about.REGION, appliance.server)
    assert about_version == appliance.region()[-1]


@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1402112])
def test_about_zone(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Open `About` modal and check the value of Zone.

    Bugzilla:
        1402112
    """
    about_version = about.get_detail(about.ZONE, appliance.server)
    assert about_version == appliance.server.zone.name
