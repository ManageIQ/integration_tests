# -*- coding: utf-8 -*-

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance import ViaREST
from cfme.utils.update import update
from cfme.fixtures.pytest_store import store

pytestmark = [test_requirements.generic_objects]


@pytest.mark.sauce
@pytest.mark.uncollectif(lambda: store.current_appliance.version < '5.9')
@pytest.mark.parametrize('context', [ViaREST])
@pytest.mark.tier(3)
def test_generic_object_definition_crud(appliance, context):
    """
    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: critical
        initialEstimate: 1/30h
    """
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name="rest_generic_class{}".format(fauxfactory.gen_alphanumeric()),
            description="Generic Object Definition",
            attributes={"addr01": "string"},
            associations={"services": "Service"},
            methods=["hello_world"])
        assert definition.exists

        with update(definition):
            definition.attributes = {"new_address": "string"}
        rest_definition = appliance.rest_api.collections.generic_object_definitions.get(
            name=definition.name)
        assert "new_address" in rest_definition.properties['attributes']
        assert "addr01" not in rest_definition.properties['attributes']

        definition.delete()
        assert not definition.exists
