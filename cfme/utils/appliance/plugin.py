import typing
from typing import cast
from typing import ForwardRef
from typing import Generic
from typing import overload
from typing import Type
from typing import TypeVar
from weakref import proxy
from weakref import WeakKeyDictionary

import attr
from cached_property import cached_property

# Avoid import cycles.
if typing.TYPE_CHECKING:
    from cfme.utils.appliance import IPAppliance
else:
    IPAppliance = ForwardRef('IPAppliance')


class AppliancePluginException(Exception):
    """Base class for all custom exceptions raised from plugins."""


TAppliancePlugin = TypeVar('TAppliancePlugin', bound='AppliancePlugin')
TPluginDescriptor = TypeVar('TPluginDescriptor', bound='AppliancePluginDescriptor')


@attr.s(slots=True)
class AppliancePluginDescriptor(Generic[TAppliancePlugin]):
    plugin_type: Type[TAppliancePlugin] = attr.ib()
    args = attr.ib()
    kwargs = attr.ib()
    cache = attr.ib(init=False, default=attr.Factory(WeakKeyDictionary), repr=False)

    @overload
    def __get__(self, instance: None, owner: Type[IPAppliance]) -> 'AppliancePluginDescriptor':
        ...

    @overload # NOQA  -- flake8 is not up to date about the overload
    def __get__(self, instance: IPAppliance, owner: Type[IPAppliance]) -> TAppliancePlugin:
        ...

    def __get__(self, instance, owner): # NOQA  -- flake8 is not up to date about the overload
        if instance is None:
            return self

        if instance not in self.cache:
            plugin = self.plugin_type(instance, *self.args, **self.kwargs)
            self.cache[instance] = plugin
        result = self.cache[instance]
        return result


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

    appliance: IPAppliance = attr.ib(repr=False, converter=proxy)

    @cached_property
    def logger(self):
        # TODO: Change when appliance gets its own
        from cfme.utils.log import logger
        return logger

    @classmethod
    def declare(cls: Type['AppliancePlugin'], *args, **kwargs):
        # There is probably no other way to make the descriptor working nicely with PyCharm due to
        # https://youtrack.jetbrains.com/issue/PY-26184
        # Let's cast to the target type as a workaround.
        return cast(cls, AppliancePluginDescriptor(cls, args, kwargs))
