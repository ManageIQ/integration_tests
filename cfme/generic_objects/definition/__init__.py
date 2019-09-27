# -*- coding: utf-8 -*-
import attr
import importscan
import sentaku

from cfme.generic_objects.definition.button_groups import GenericObjectButtonGroupsCollection
from cfme.generic_objects.definition.button_groups import GenericObjectButtonsCollection
from cfme.generic_objects.instance import GenericObjectInstanceCollection
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.update import Updateable


@attr.s
class GenericObjectDefinition(BaseEntity, Updateable, sentaku.modeling.ElementMixin):
    """Generic Objects Definition class to context switch between UI and REST.

    Read/Update/Delete functionality.
    """
    _collections = {
        'generic_objects': GenericObjectInstanceCollection,
        'generic_object_groups_buttons': GenericObjectButtonGroupsCollection,
        'generic_object_buttons': GenericObjectButtonsCollection
    }

    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    exists = sentaku.ContextualProperty()
    add_button = sentaku.ContextualMethod()
    add_button_group = sentaku.ContextualMethod()
    generic_objects = sentaku.ContextualProperty()
    generic_object_buttons = sentaku.ContextualProperty()
    instance_count = sentaku.ContextualProperty()

    name = attr.ib()
    description = attr.ib()
    attributes = attr.ib(default=None)  # e.g. {'address': 'string'}
    associations = attr.ib(default=None)  # e.g. {'services': 'Service'}
    methods = attr.ib(default=None)  # e.g. ['method1', 'method2']
    custom_image_file_path = attr.ib(default=None)
    rest_response = attr.ib(default=None, init=False)


@attr.s
class GenericObjectDefinitionCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = GenericObjectDefinition

    create = sentaku.ContextualMethod()
    all = sentaku.ContextualMethod()


from cfme.generic_objects.definition import rest, ui  # NOQA last for import cycles
importscan.scan(rest)
importscan.scan(ui)
