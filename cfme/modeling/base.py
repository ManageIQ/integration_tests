import attr
from collections import Callable

from cached_property import cached_property

from cfme.utils.appliance import NavigatableMixin


class ApplianceCollections(object):
    """Caches instances of collection objects for use by the collections accessor

    The appliance object has a ``collections`` attribute. This attribute is an instance
    of this class. It is initialized with an appliance object and locally stores a cache
    of all known good collections.
    """
    _collection_classes = None

    def __init__(self, appliance):
        self._collection_cache = {}
        self.appliance = appliance
        if not self._collection_classes:
            self.load_collections()
        for collection, cls in self._collection_classes.items():
            self._collection_cache[collection] = cls(self.appliance)

    def load_collections(self):
        """Loads the collection definitions from the entrypoints system"""
        from pkg_resources import iter_entry_points
        ApplianceCollections._collection_classes = {
            ep.name: ep.resolve() for ep in iter_entry_points('manageiq.appliance_collections')
        }

    def __getattr__(self, name):
        try:
            return self._collection_cache[name]
        except KeyError:
            raise AttributeError('Collection [{}] not known to applinace'.format(name))


class ObjectCollections(ApplianceCollections):
    def __init__(self, parent):
        self._collection_cache = {}
        self.parent = parent
        self.appliance = self.parent.appliance
        self.collections = self.parent._collections
        self.load_collections()

    def load_collections(self):
        for collection, cls_and_or_filter in self.collections.items():
            filter = {'parent': self.parent}
            if isinstance(cls_and_or_filter, tuple):
                filter.update(cls_and_or_filter[1])
                cls = cls_and_or_filter[0]
            else:
                cls = cls_and_or_filter
            collection_instance = cls(self.appliance, filters=filter)
            self._collection_cache[collection] = collection_instance


@attr.s
class BaseCollection(NavigatableMixin):
    """Class for helping create consistent Collections

    The BaseCollection class is responsible for ensuring two things:

    1) That the API consistently has the first argument passed to it
    2) That that first argument is an appliance instance

    This class works in tandem with the entrypoint loader which ensures that the correct
    argument names have been used.
    """

    ENTITY = None

    parent = attr.ib()
    filters = attr.ib(default=attr.Factory(dict))

    @property
    def appliance(self):
        if isinstance(self.parent, BaseEntity):
            return self.parent.appliance
        else:
            return self.parent

    @classmethod
    def for_appliance(cls, appliance, *k, **kw):
        return cls(appliance)

    @classmethod
    def for_entity(cls, obj, *k, **kw):
        return cls(obj, *k, **kw)

    @classmethod
    def for_entity_with_filter(cls, obj, filt, *k, **kw):
        return cls.for_entity(obj, *k, **kw).filter(filt)

    def instantiate(self, *args, **kwargs):
        return self.ENTITY.from_collection(self, *args, **kwargs)

    def filter(self, filter):
        filters = self.filters.copy()
        filters.update(filter)
        return attr.evolve(self, filters=filters)


@attr.s
class BaseEntity(NavigatableMixin):
    """Class for helping create consistent entitys

    The BaseEntity class is responsible for ensuring two things:

    1) That the API consistently has the first argument passed to it
    2) That that first argument is a collection instance

    This class works in tandem with the entrypoint loader which ensures that the correct
    argument names have been used.
    """

    parent = attr.ib(repr=False)  # This is the collection

    @property
    def appliance(self):
        return self.parent.appliance

    @classmethod
    def from_collection(cls, collection, *k, **kw):
        return cls(collection, *k, **kw)

    @cached_property
    def collections(self):
        return ObjectCollections(self)


@attr.s
class CollectionProperty(object):
    type_or_get_type = attr.ib(validator=attr.validators.instance_of((Callable, type)))

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if not isinstance(self.type_or_get_type, type):
            self.type_or_get_type = self.type_or_get_type()
        return self.type_or_get_type.for_entity_with_filter(instance, {'parent': instance})
