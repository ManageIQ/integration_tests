import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.manual,
    test_requirements.service
]


@pytest.mark.manual
@pytest.mark.tier(3)
def test_changing_action_order_in_catalog_bundle_should_not_removes_resource():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        testtype: functional
        startsin: 5.8
        tags: service
    Bugzilla:
        1615853
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_request_filter_on_request_page():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1498237
    """
    pass
