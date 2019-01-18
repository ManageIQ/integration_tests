import pytest

from cfme import test_requirements


pytestmark = [test_requirements.rest]


@pytest.mark.manual
def test_custom_button_crud_via_rest():
    """ In this Test case we verify the functionality of custom button using rest api

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: custom_button
        tags: custom_button
        testSteps:
            1. POST method to create the custom button
            2. POST method to edit the custom button
            3. Delete method to delete the custom button
    """
    pass


@pytest.mark.manual
def test_custom_button_edit_via_rest_put():
    """
    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: custom_button
        tags: custom_button
        testSteps:
            1. Create custom button
            2. Use Put method to edit the custom button
            3. Delete custom button
    """
    pass


@pytest.mark.manual
def test_custom_button_edit_via_rest_patch():
    """
    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: custom_button
        tags: custom_button
        testSteps:
            1. Create Custom button
            2. Edit custom button using Patch method
            3. Delete custom button
    """
    pass
