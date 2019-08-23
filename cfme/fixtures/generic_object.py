import fauxfactory
import pytest

from cfme.services.myservice import MyService
from cfme.utils.appliance import ViaREST
from cfme.utils.rest import assert_response


@pytest.fixture(scope="module")
def gen_rest_service(appliance):
    """Simple service create with rest for generic object association"""

    rest_service = appliance.rest_api.collections.services.action.create(
        name=fauxfactory.gen_numeric_string(16, start="gen_rest_serv", separator="-"), display=True
    )[0]

    yield rest_service
    if rest_service.exists:
        rest_service.action.delete()


@pytest.fixture(scope="module")
def generic_definition(appliance):
    """Generic object definition or class"""

    with appliance.context.use(ViaREST):
        definition = appliance.collections.generic_object_definitions.create(
            name=fauxfactory.gen_numeric_string(17, start="gen_rest_class", separator="-"),
            description="Generic Object Definition",
            attributes={"addr01": "string"},
            associations={"services": "Service"},
            methods=["add_vm", "remove_vm"],
        )
        yield definition
        definition.delete_if_exists()


@pytest.fixture(scope="module")
def generic_object(generic_definition, gen_rest_service, appliance):
    """Generic object associated with service"""

    myservice = MyService(appliance, name=gen_rest_service.name)

    with appliance.context.use(ViaREST):
        instance = appliance.collections.generic_objects.create(
            name=fauxfactory.gen_numeric_string(20, start="gen_rest_instance", separator="-"),
            definition=generic_definition,
            attributes={"addr01": "Test Address"},
            associations={"services": [gen_rest_service]},
        )
        instance.my_service = myservice
        yield instance
        instance.delete_if_exists()


@pytest.fixture(scope="module")
def add_generic_object_to_service(appliance, gen_rest_service, generic_object):
    """Add generic object as resource of service"""

    with appliance.context.use(ViaREST):
        gen_rest_service.action.add_resource(
            resource=appliance.rest_api.collections.generic_objects.find_by(
                name=generic_object.name
            )[0]._ref_repr()
        )
        assert_response(appliance)
    return generic_object
