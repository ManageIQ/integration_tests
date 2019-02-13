import pytest
import fauxfactory

from cfme import test_requirements
from cfme.tests.automate.custom_button import CLASS_MAP, OBJ_TYPE, OBJ_TYPE_59

pytestmark = [test_requirements.rest]


@pytest.mark.tier(2)
@pytest.mark.uncollectif(
    lambda appliance, obj_type: obj_type not in OBJ_TYPE_59 and appliance.version < "5.10"
)
@pytest.mark.parametrize("obj_type", OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE])
def test_custom_button_group_crud_via_rest(appliance, obj_type):
    """ In this Test case we verify the crud functionality of custom button group using rest api

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. POST method to create the custom button group
            2. POST method to edit the custom button group
            3. Delete method to delete the custom button group
    """
    gp_coll = appliance.rest_api.collections.custom_button_sets

    # create
    _gp = {
        "name": "gp_{}".format(fauxfactory.gen_alphanumeric(3)),
        "description": "disc_{}".format(fauxfactory.gen_alphanumeric(3)),
        "set_data": {
            "button_icon": "ff ff-network-switch",
            "display": True,
            "applies_to_class": CLASS_MAP[obj_type]["rest"],
        },
    }
    gp = gp_coll.action.create(_gp)[0]
    assert gp.exists
    assert gp.description == _gp.get("description")

    # edit
    _gp_edited = {
        "name": "edited_{}".format(gp.name),
        "description": "edited".format(gp.description),
    }
    gp.action.edit(**_gp_edited)
    gp.reload()
    assert gp.name == _gp_edited.get("name")
    assert gp.description == _gp_edited.get("description")

    # delete
    gp_coll.action.delete(gp)
    assert not gp.exists


@pytest.mark.tier(2)
@pytest.mark.uncollectif(
    lambda appliance, obj_type: obj_type not in OBJ_TYPE_59 and appliance.version < "5.10"
)
@pytest.mark.parametrize("obj_type", OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE])
def test_custom_button_crud_via_rest(appliance, obj_type):
    """ In this Test case we verify the functionality of custom button using rest api

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. POST method to create the custom button
            2. POST method to edit the custom button
            3. Delete method to delete the custom button
    """
    button_coll = appliance.rest_api.collections.custom_buttons

    # create
    _btn = {
        "applies_to_class": CLASS_MAP[obj_type]["rest"],
        "description": "btn_{}".format(fauxfactory.gen_alphanumeric(3)),
        "name": "disc_{}".format(fauxfactory.gen_alphanumeric(3)),
        "options": {"button_color": "#4727ff", "button_icon": "ff fa-user", "display": True},
        "resource_action": {"ae_class": "PROCESS", "ae_namespace": "SYSTEM"},
        "visibility": {"roles": ["_ALL_"]},
    }

    btn = button_coll.action.create(_btn)[0]
    assert btn.exists
    assert btn.description == _btn.get("description")

    # edit
    _btn_edited = {
        "name": "edited_{}".format(btn.name),
        "description": "edited".format(btn.description),
    }
    btn.action.edit(**_btn_edited)
    btn.reload()
    assert btn.name == _btn_edited.get("name")
    assert btn.description == _btn_edited.get("description")

    # delete
    button_coll.action.delete(btn)
    assert not btn.exists


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
        casecomponent: CustomButton
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
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create Custom button
            2. Edit custom button using Patch method
            3. Delete custom button
    """
    pass
