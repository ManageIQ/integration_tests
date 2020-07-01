from typing import Type
from typing import TypeVar
from weakref import proxy
from weakref import WeakKeyDictionary

import attr
from cached_property import cached_property

T = TypeVar('T')


class AppliancePluginException(Exception):
    """Base class for all custom exceptions raised from plugins."""


@attr.s(slots=True)
class AppliancePluginDescriptor:
    cls = attr.ib()
    args = attr.ib()
    kwargs = attr.ib()
    cache = attr.ib(init=False, default=attr.Factory(WeakKeyDictionary), repr=False)

    def __get__(self, o, t=None):
        if o is None:
            return self

        if o not in self.cache:
            self.cache[o] = new_instance = self.cls(o, *self.args, **self.kwargs)
            return new_instance

        return self.cache[o]


@attr.s
class AppliancePlugin:
    """Base class for all appliance plugins.

    Usage:

        .. code-block:: python

            class IPAppliance(object):
                # ...

                foo = FooPlugin.declare(parameter='value')

    Instance of such plugin is then created upon first access.
    """
    # appliance: IPAppliance = attr.ib(repr=False, converter=proxy)
    appliance = attr.ib(repr=False, converter=proxy)

    @cached_property
    def logger(self):
        # TODO: Change when appliance gets its own
        from cfme.utils.log import logger
        return logger

    @classmethod
    def declare(cls: Type[T], **kwargs) -> T:
        return AppliancePluginDescriptor(cls, (), kwargs)
