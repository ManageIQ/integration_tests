import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.rest import assert_response

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([LenovoProvider])
]


def test_get_switch(physical_switch, appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    existent_switch = appliance.rest_api.get_entity('switches', physical_switch.id)
    existent_switch.reload()
    assert_response(appliance)


def test_get_nonexistent_physical_switch(appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    nonexistent = appliance.rest_api.get_entity('switches', 999999)
    with pytest.raises(Exception, match='ActiveRecord::RecordNotFound'):
        nonexistent.reload()
    assert_response(appliance, http_status=404)


def test_invalid_action(physical_switch, appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    payload = {
        "action": "invalid_action"
    }
    with pytest.raises(Exception, match='Api::BadRequestError'):
        appliance.rest_api.post(physical_switch.href, **payload)


def test_refresh_physical_switch(appliance, physical_switch):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    assert getattr(physical_switch.action, "refresh")()
    assert_response(appliance)
