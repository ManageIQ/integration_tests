import attr
import importscan
import sentaku

from cfme.common import Taggable
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.update import Updateable


@attr.s
class GenericObjectInstance(BaseEntity, Updateable, sentaku.modeling.ElementMixin, Taggable):
    """Generic Objects class to context switch between REST and Automate.

    Read/Update/Delete functionality.
    """
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    add_tag = sentaku.ContextualMethod()
    remove_tag = sentaku.ContextualMethod()
    get_tags = sentaku.ContextualMethod()
    exists = sentaku.ContextualProperty()

    name = attr.ib()
    definition = attr.ib()  # generic object definition
    attributes = attr.ib(default=None)  # e.g. {'address': 'Test Address'}
    associations = attr.ib(default=None)  # e.g. {'services': [myservice1, myservice2]}
    rest_response = attr.ib(default=None, init=False)
    my_service = attr.ib(default=None)   # my_service object with instance assignment


@attr.s
class GenericObjectInstanceCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = GenericObjectInstance

    create = sentaku.ContextualMethod()
    all = sentaku.ContextualMethod()


from cfme.generic_objects.instance import rest, ui  # NOQA last for import cycles
importscan.scan(rest)
importscan.scan(ui)
