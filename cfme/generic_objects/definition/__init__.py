# -*- coding: utf-8 -*-

import attr
import importscan
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

    name = attr.ib()
    description = attr.ib()
    attributes = attr.ib(default=None)  # e.g. {'address': 'string'}
    associations = attr.ib(default=None)  # e.g. {'services': 'Service'}
    methods = attr.ib(default=None)  # e.g. ['method1', 'method2']
    rest_response = attr.ib(default=None, init=False)


@attr.s
class GenericObjectDefinitionCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = GenericObjectDefinition

    create = sentaku.ContextualMethod()


from . import rest  # NOQA last for import cycles
importscan.scan(rest)
