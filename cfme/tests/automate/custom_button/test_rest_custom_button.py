import pytest
import fauxfactory

from cfme import test_requirements
from cfme.utils.rest import (
    assert_response,
    delete_resources_from_collection,
    delete_resources_from_detail,
    query_resource_attributes,
)
from cfme.rest import gen_data
from cfme.tests.automate.custom_button import CLASS_MAP, OBJ_TYPE, OBJ_TYPE_59
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.rest,
    pytest.mark.uncollectif(
        lambda appliance, obj_type: obj_type not in OBJ_TYPE_59 and appliance.version < "5.10"
    ),
    pytest.mark.parametrize("obj_type", OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE]),
]


class TestCustomButtonRESTAPI(object):
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
            casecomponent: CustomButton
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
            casecomponent: CustomButton
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
            casecomponent: CustomButton
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
            casecomponent: CustomButton
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
            casecomponent: CustomButton
            tags: custom_button
        """

        entities, _type = buttons_groups
        num_entities = len(entities)
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_entities)]
        new = [{"name": "Edited_{}".format(u), "description": "Edited_{}".format(u)} for u in uniq]
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
