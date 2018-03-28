# -*- coding: utf-8 -*-

import attr
import importscan
import sentaku

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.update import Updateable


@attr.s
class GenericObjectInstance(BaseEntity, Updateable, sentaku.modeling.ElementMixin):
    """Generic Objects class to context switch between REST and Automate.

    Read/Update/Delete functionality.
    """
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    exists = sentaku.ContextualProperty()

    name = attr.ib()
    definition = attr.ib()  # generic object definition
    attributes = attr.ib(default=None)  # e.g. {'address': 'Test Address'}
    associations = attr.ib(default=None)  # e.g. {'services': [myservice1, myservice2]}
    rest_response = attr.ib(default=None, init=False)


@attr.s
class GenericObjectInstanceCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = GenericObjectInstance

    create = sentaku.ContextualMethod()


from . import rest, ui  # NOQA last for import cycles
importscan.scan(rest)
importscan.scan(ui)
