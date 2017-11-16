# -*- coding: utf-8 -*-

from cfme.generic_objects.definition import (
    GenericObjectDefinition,
    GenericObjectDefinitionCollection
)
from cfme.utils.appliance.implementations.rest import ViaREST
from cfme.utils.rest import assert_response, create_resource


@GenericObjectDefinitionCollection.create.external_implementation_for(ViaREST)
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


@GenericObjectDefinition.update.external_implementation_for(ViaREST)
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


@GenericObjectDefinition.delete.external_implementation_for(ViaREST)
def delete(self):
    definition = self.appliance.rest_api.collections.generic_object_definitions.find_by(
        name=self.name)

    if not definition:
        self.rest_response = None
        return

    definition = definition[0]
    definition.action.delete()
    assert_response(self.appliance)
    self.rest_response = self.appliance.rest_api.response


@GenericObjectDefinition.exists.external_getter_implemented_for(ViaREST)
def exists(self):
    return bool(
        self.appliance.rest_api.collections.generic_object_definitions.find_by(name=self.name))
