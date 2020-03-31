import fauxfactory
import pytest

from cfme import test_requirements
from cfme.rest import gen_data
from cfme.tests.automate.custom_button import CLASS_MAP
from cfme.tests.automate.custom_button import OBJ_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import query_resource_attributes
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.custom_button,
    pytest.mark.uncollectif(
        lambda appliance, obj_type: appliance.version >= "5.11" and obj_type == "LOAD_BALANCER",
        reason="Load Balancer not supported from version 5.11"
    ),
    pytest.mark.parametrize("obj_type", OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE],
                            scope="module"),
]


@pytest.fixture(scope="module")
def group_rest(request, appliance, obj_type):
    # create group (custom button set)
    button_type = CLASS_MAP[obj_type]["rest"]
    response = gen_data.custom_button_sets(request, appliance, button_type)
    assert_response(appliance)
    return response[0]


@pytest.fixture(scope="module")
def buttons_rest(request, appliance, obj_type):
    # create unassigned button (custom button)
    button_type = CLASS_MAP[obj_type]["rest"]
    response = gen_data.custom_buttons(request, appliance, button_type, num=2)
    assert_response(appliance)
    return response


class TestCustomButtonRESTAPI:
    @pytest.fixture(params=["custom_button_sets", "custom_buttons"], ids=["Group", "Button"])
    def buttons_groups(self, request, appliance, obj_type):
        button_type = CLASS_MAP[obj_type]["rest"]
        num_conditions = 2
        response = getattr(gen_data, request.param)(
            request, appliance, button_type, num=num_conditions
        )
        assert_response(appliance)
        assert len(response) == num_conditions
        return response, request.param

    def test_query_attributes(self, buttons_groups, soft_assert):
        """Tests access to custom button/group attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: ndhandre
            initialEstimate: 1/4h
            caseimportance: low
            caseposneg: positive
            testtype: functional
            startsin: 5.9
            casecomponent: Rest
            tags: custom_button
        """
        response, _ = buttons_groups
        query_resource_attributes(response[0], soft_assert=soft_assert)

    def test_create(self, appliance, buttons_groups):
        """Tests create custom button/group.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: ndhandre
            initialEstimate: 1/4h
            caseimportance: medium
            caseposneg: positive
            testtype: functional
            startsin: 5.9
            casecomponent: Rest
            tags: custom_button
        """
        entities, _type = buttons_groups

        for entity in entities:
            record = getattr(appliance.rest_api.collections, _type).get(id=entity.id)
            assert record.description == entity.description

    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_from_detail(self, buttons_groups, method):
        """Tests delete custom button/group from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: ndhandre
            initialEstimate: 1/4h
            caseimportance: medium
            caseposneg: positive
            testtype: functional
            startsin: 5.9
            casecomponent: Rest
            tags: custom_button
        """
        entities, _ = buttons_groups
        delete_resources_from_detail(entities, method=method, num_sec=100, delay=5)

    def test_delete_from_collection(self, buttons_groups):
        """Tests delete custom button/group from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: ndhandre
            initialEstimate: 1/4h
            caseimportance: low
            caseposneg: positive
            testtype: functional
            startsin: 5.9
            casecomponent: Rest
            tags: custom_button
        """
        entities, _ = buttons_groups
        delete_resources_from_collection(entities, num_sec=100, delay=5)

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_edit(self, buttons_groups, appliance, from_detail):
        """Tests edit custom button/group.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: ndhandre
            initialEstimate: 1/4h
            caseimportance: medium
            caseposneg: positive
            testtype: functional
            startsin: 5.9
            casecomponent: Rest
            tags: custom_button
        """

        entities, _type = buttons_groups
        num_entities = len(entities)
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_entities)]
        new = [{"name": f"Edited_{u}", "description": f"Edited_{u}"} for u in uniq]
        if from_detail:
            edited = []
            for index in range(num_entities):
                edited.append(entities[index].action.edit(**new[index]))
                assert_response(appliance)
        else:
            for index in range(num_entities):
                new[index].update(entities[index]._ref_repr())
            edited = getattr(appliance.rest_api.collections, _type).action.edit(*new)
            assert_response(appliance)
        assert len(edited) == num_entities
        for index, condition in enumerate(entities):
            record, __ = wait_for(
                lambda: getattr(appliance.rest_api.collections, _type).find_by(
                    description=new[index]["description"]
                )
                or False,
                num_sec=100,
                delay=5,
                message="Find a test condition",
            )
            condition.reload()
            assert condition.description == edited[index].description == record[0].description


@pytest.mark.meta(automates=[1737449, 1745198])
def test_associate_unassigned_buttons_rest(appliance, group_rest, buttons_rest):
    """Test associate unassigned button with group

    Bugzilla:
        1737449
        1745198

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        startsin: 5.10
        casecomponent: CustomButton
        tags: custom_button
    """

    # Add associate unassigned buttons to group with rest
    set_data = group_rest.set_data
    set_data["button_order"] = [int(b.id) for b in buttons_rest]
    data = {"set_data": set_data}
    group_rest.action.edit(**data)
    assert_response(appliance)

    # Check association with UI
    group_collection = appliance.collections.button_groups
    gp = group_collection.ENTITY.from_id(group_collection, group_rest.id)

    # Point to new object type so that teardown button(removed with rest) and new buttons, group
    # (created with rest) reflect on UI without any selenium exception.
    view = navigate_to(gp, "ObjectType")
    view.browser.refresh()

    view = navigate_to(gp, "Details")
    ui_assinged_btns = {btn["Text"].text for btn in view.assigned_buttons}

    assert ui_assinged_btns == {btn.name for btn in buttons_rest}
