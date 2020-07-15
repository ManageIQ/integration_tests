from collections.abc import Callable

import attr
from cached_property import cached_property
from navmazing import NavigationDestinationNotFound
from widgetastic.exceptions import NoSuchElementException
from widgetastic.exceptions import RowNotFound
from widgetastic.utils import VersionPick
from widgetastic_patternfly import CandidateNotFound

from cfme.exceptions import ItemNotFound
from cfme.exceptions import KeyPairNotFound
from cfme.exceptions import RestLookupError
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError


def load_appliance_collections():
    from pkg_resources import iter_entry_points
    return {
        ep.name: ep.resolve() for ep in iter_entry_points('manageiq.appliance_collections')
    }


@attr.s
class EntityCollections:
    """Caches instances of collection objects for use by the collections accessor

    The appliance object has a ``collections`` attribute. This attribute is an instance
    of this class. It is initialized with an appliance object and locally stores a cache
    of all known good collections.
    """
    _parent = attr.ib(repr=False, eq=False, hash=False)
    _available_collections = attr.ib(repr=False, eq=False, hash=False)
    _filters = attr.ib(eq=False, hash=False, default=attr.Factory(dict))
    _collection_cache = attr.ib(repr=False, eq=False, hash=False, init=False,
                                default=attr.Factory(dict))

    @classmethod
    def for_appliance(cls, appliance):
        return cls(parent=appliance, available_collections=load_appliance_collections())

    @classmethod
    def for_entity(cls, entity, collections):
        return cls(parent=entity, available_collections=collections, filters={'parent': entity})

    @classmethod
    def declared(cls, **spec):
        """returns a cached property named collections for use in entities"""
        @cached_property
        def collections(self):
            return cls.for_entity(self, spec)
        collections.spec = spec
        return collections

    def __dir__(self):
        internal_dir = dir(super())
        return internal_dir + list(self._available_collections.keys())

    def __getattr__(self, name):
        if name not in self._available_collections:
            sorted_collection_keys = sorted(self._available_collections)
            raise AttributeError('Collection [{}] not known to object, available collections: {}'
                                 .format(name, sorted_collection_keys))
        if name not in self._collection_cache:
            item_filters = self._filters.copy()
            cls_and_or_filter = self._available_collections[name]
            if isinstance(cls_and_or_filter, tuple):
                item_filters.update(cls_and_or_filter[1])
                cls_or_verpick = cls_and_or_filter[0]
            else:
                cls_or_verpick = cls_and_or_filter
            # Now check whether we verpick the collection or not
            if isinstance(cls_or_verpick, VersionPick):
                cls = cls_or_verpick.pick(self._parent.appliance.version)
                try:
                    logger.info(
                        '[COLLECTIONS] Version picked collection %s as %s.%s',
                        name, cls.__module__, cls.__name__)
                except (AttributeError, TypeError, ValueError):
                    logger.exception('[COLLECTIONS] Is the collection %s truly a collection?', name)
            else:
                cls = cls_or_verpick
            self._collection_cache[name] = cls(self._parent, filters=item_filters)
        return self._collection_cache[name]


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

    parent = attr.ib(repr=False)
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

    parent = attr.ib(repr=False)  # This is the collection or not

    # TODO This needs removing as we need proper __eq__ on objects, but it is part of a
    #      much larger discussion
    __hash__ = object.__hash__

    @property
    def appliance(self):
        return self.parent.appliance

    @classmethod
    def from_collection(cls, collection, *k, **kw):
        return cls(collection, *k, **kw)

    @cached_property
    def collections(self):
        try:
            spec = self._collections
        except AttributeError:
            raise AttributeError("collections")

        return EntityCollections.for_entity(self, spec)

    @property
    def exists(self):
        try:
            navigate_to(self, "Details")
        except (
            CandidateNotFound,
            ItemNotFound,
            KeyPairNotFound,
            NameError,
            NavigationDestinationNotFound,
            NoSuchElementException,
            RestLookupError,
            RowNotFound,
            TimedOutError,
        ):
            return False
        else:
            return True

    def delete_if_exists(self, *args, **kwargs):
        """Combines ``.exists`` and ``.delete()`` as a shortcut for ``request.addfinalizer``

        Raises
            NotImplementedError: If the ``.delete()`` is not implemented for the object
        Returns: True if object existed and delete was initiated, False otherwise
        """
        if self.exists:
            try:
                self.delete(*args, **kwargs)
                return True
            except AttributeError:
                raise NotImplementedError("Delete method is not implemented.")
        return False

    @property
    def expected_details_title(self):
        """Provides expected Details/Summary Page title; which mostly used in EntityDetailsViews

        .. code-block:: python
            expected_title = self.context['object'].expected_details_title
        """
        return f"{self.name} (Summary)"

    @property
    def expected_details_breadcrumb(self):
        """Provides expected Details/Summary Page breadcrumb active location;
        which mostly used in EntityDetailsViews

        .. code-block:: python
            expected_breadcrumb = self.context['object'].expected_details_breadcrumb
        """
        return f"{self.name} (Summary)"


@attr.s
class CollectionProperty:
    type_or_get_type = attr.ib(validator=attr.validators.instance_of((Callable, type)))

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if not isinstance(self.type_or_get_type, type):
            self.type_or_get_type = self.type_or_get_type()
        return self.type_or_get_type.for_entity_with_filter(instance, {'parent': instance})


def _walk_to_obj_root(obj):
    old = None
    while True:
        if old is obj:
            break
        yield obj
        old = obj
        try:
            obj = obj.parent
        except AttributeError:
            pass


def parent_of_type(obj, klass):
    for x in _walk_to_obj_root(obj):
        if isinstance(x, klass):
            return x
