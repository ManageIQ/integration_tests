# -*- coding: utf-8 -*-

import attr

import sentaku

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.update import Updateable


@attr.s
class GenericObjectDefinition(BaseEntity, Updateable, sentaku.modeling.ElementMixin):
    """Generic Objects Definition class to context switch between UI and REST.

    Read/Update/Delete functionality.
    """
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    exists = sentaku.ContextualProperty()

    name = attr.ib(default=None)
    description = attr.ib(default=None)
    attributes = attr.ib(default=None)
    associations = attr.ib(default=None)
    methods = attr.ib(default=None)

    def __attrs_post_init__(self):
        self.rest_response = None


@attr.s
class GenericObjectDefinitionCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = GenericObjectDefinition

    create = sentaku.ContextualMethod()


from . import rest  # NOQA last for import cycles
sentaku.register_external_implementations_in(rest)
