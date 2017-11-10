# -*- coding: utf-8 -*-

import pytest
import fauxfactory

from cfme import test_requirements
from cfme.utils.appliance import ViaREST
from cfme.utils.update import update
from fixtures.pytest_store import store


pytestmark = [test_requirements.generic_objects]


@pytest.mark.uncollectif(lambda: store.current_appliance.version < '5.9')
@pytest.mark.parametrize('context', [ViaREST])
def test_generic_object_definition_crud(appliance, context):
    with appliance.context.use(context):
        definitions_collection = appliance.collections.generic_object_definitions
        definition = definitions_collection.create(
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
