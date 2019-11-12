from cfme.generic_objects.definition import GenericObjectDefinition
from cfme.generic_objects.definition import GenericObjectDefinitionCollection
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.rest import ViaREST
from cfme.utils.rest import assert_response
from cfme.utils.rest import create_resource


# collection methods
@MiqImplementationContext.external_for(GenericObjectDefinitionCollection.create, ViaREST)
def create(self, name, description, attributes=None, associations=None, methods=None):
    body = {'name': name, 'description': description, 'properties': {}}
    properties = body['properties']

    if attributes:
        properties['attributes'] = attributes
    if associations:
        properties['associations'] = associations
    if methods:
        properties['methods'] = methods

    create_resource(self.appliance.rest_api, 'generic_object_definitions', [body])
    assert_response(self.appliance)
    rest_response = self.appliance.rest_api.response

    entity = self.instantiate(
        name=name, description=description, attributes=attributes, associations=associations,
        methods=methods
    )
    entity.rest_response = rest_response
    return entity


@MiqImplementationContext.external_for(GenericObjectDefinitionCollection.all, ViaREST)
def all(self):
    rest_generic_object_definitions = (
        self.appliance.rest_api.collections.generic_object_definitions.all
    )
    return [
        self.instantiate(name=gobj_def.name, description=gobj_def.description)
        for gobj_def in rest_generic_object_definitions
    ]


# entity methods
@MiqImplementationContext.external_for(GenericObjectDefinition.update, ViaREST)
def update(self, updates):
    definition = self.appliance.rest_api.collections.generic_object_definitions.find_by(
        name=self.name)

    if not definition:
        self.rest_response = None
        return

    definition = definition[0]

    top = ['name', 'description']
    prop = ['attributes', 'associations', 'methods']

    body = {}
    properties = body['properties'] = {}

    for key in top:
        new = updates.get(key)
        body.update({} if new is None else {key: new})
    for key in prop:
        new = updates.get(key)
        properties.update({} if new is None else {key: new})

    definition.action.edit(**body)
    assert_response(self.appliance)
    self.rest_response = self.appliance.rest_api.response


@MiqImplementationContext.external_for(GenericObjectDefinition.delete, ViaREST)
def delete(self):
    definition = self.appliance.rest_api.collections.generic_object_definitions.find_by(
        name=self.name)

    if not definition:
        self.rest_response = None
        return

    definition = definition[0]
    instances = self.appliance.rest_api.collections.generic_objects.find_by(
        generic_object_definition_id=definition.id
    )
    for instance in instances:
        instance.action.delete()

    definition.action.delete()
    assert_response(self.appliance)
    self.rest_response = self.appliance.rest_api.response


@MiqImplementationContext.external_for(GenericObjectDefinition.exists.getter, ViaREST)
def exists(self):
    return bool(
        self.appliance.rest_api.collections.generic_object_definitions.find_by(name=self.name))
