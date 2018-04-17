# -*- coding: utf-8 -*-

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.services.myservice import MyService
from cfme.utils.appliance import ViaREST, ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update

pytestmark = [test_requirements.generic_objects]


@pytest.mark.sauce
@pytest.mark.uncollectif(lambda appliance: appliance.version < '5.9')
@pytest.mark.parametrize('context', [ViaREST])
def test_generic_objects_crud(appliance, context, request):
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name='rest_generic_class{}'.format(fauxfactory.gen_alphanumeric()),
            description='Generic Object Definition',
            attributes={'addr01': 'string'},
            associations={'services': 'Service'}
        )
        assert definition.exists
        request.addfinalizer(definition.delete)

        myservices = []
        for _ in range(2):
            service_name = 'rest_service_{}'.format(fauxfactory.gen_alphanumeric())
            rest_service = appliance.rest_api.collections.services.action.create(
                name=service_name,
                display=True
            )
            rest_service = rest_service[0]
            request.addfinalizer(rest_service.action.delete)
            myservices.append(MyService(appliance, name=service_name))
        instance = appliance.collections.generic_objects.create(
            name='rest_generic_instance{}'.format(fauxfactory.gen_alphanumeric()),
            definition=definition,
            attributes={'addr01': 'Test Address'},
            associations={'services': [myservices[0]]}
        )
        assert instance.exists
        request.addfinalizer(instance.delete)

        with update(instance):
            instance.attributes = {'addr01': 'Changed'}
            instance.associations = {'services': myservices}
        rest_instance = appliance.rest_api.collections.generic_objects.get(name=instance.name)
        rest_data = appliance.rest_api.get('{}?associations=services'.format(rest_instance.href))
        assert len(rest_data['services']) == 2
        assert rest_data['property_attributes']['addr01'] == 'Changed'

        instance.delete()
        assert not instance.exists


@pytest.mark.uncollectif(lambda appliance: appliance.version < '5.9')
@pytest.mark.parametrize('context', [ViaUI])
def test_generic_objects_crud_ui(appliance, context):
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name="rest_generic_class{}".format(fauxfactory.gen_alphanumeric()),
            description="Generic Object Definition",
            attributes={"addr01": "String"},
            associations={"services": "Service"},
            methods=["hello_world"])

        with appliance.context.use(ViaREST):
            instance = appliance.collections.generic_objects.create(
                name='rest_generic_instance{}'.format(fauxfactory.gen_alphanumeric()),
                definition=definition,
                attributes={'addr01': 'Test Address'}
            )
        view = navigate_to(instance, 'Details')
        assert view.is_displayed


def test_generic_objects_with_button_group(appliance, context, generic_object_definition,
                                           generic_services):
    group = generic_object_definition.add_button_group()
    generic_object_definition.add_button()


def test_generic_objects_with_button():
    pass


def test_generic_objects_tagging():
    pass
