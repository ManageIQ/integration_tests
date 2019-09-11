import pytest

from cfme import test_requirements


@pytest.mark.manual
@pytest.mark.tier(1)
@test_requirements.appliance
def test_automated_locale_switching():
    """
    Having the automatic locale selection selected, the appliance"s locale
    changes accordingly with user"s preferred locale in the browser.

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass
