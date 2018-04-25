# -*- coding: utf-8 -*-

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import ViaREST, ViaUI
from cfme.utils.update import update
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.generic_objects,
    pytest.mark.uncollectif(lambda appliance: appliance.version < "5.9",
                            reason="5.8 appliance doesn't support generic objects")
]


@pytest.mark.sauce
@pytest.mark.parametrize('context', [ViaREST])
def test_generic_object_definition_crud(appliance, context):
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


@pytest.mark.parametrize('context', [ViaUI])
def test_generic_object_definition_crud_ui(appliance, context, soft_assert):
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name="generic_class{}".format(fauxfactory.gen_alphanumeric()),
            description="Generic Object Definition",
            attributes={"addr01": "String"},
            associations={"services": "Service"},
            methods=["hello_world"])
        view = appliance.browser.create_view(BaseLoggedInPage)
        view.flash.assert_success_message(
            'Generic Object Class "{}" has been successfully added.'.format(definition.name))

        with update(definition):
            definition.name = '{}_updated'.format(definition.name)
            definition.attributes = {"new_address": "String"}
        view.flash.assert_success_message(
            'Generic Object Class "{}" has been successfully saved.'.format(definition.name))
        view = navigate_to(definition, 'Details')
        soft_assert(view.summary('Attributes (2)').get_text_of('new_address'))
        soft_assert(view.summary('Attributes (2)').get_text_of('addr01'))
        soft_assert(view.summary('Associations (1)').get_text_of('services'))
        definition.delete()
        view.flash.assert_success_message(
            'Generic Object Class:"{}" was successfully deleted'.format(definition.name))
