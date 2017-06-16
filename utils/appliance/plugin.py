# -*- coding: utf-8 -*-
import attr
from cached_property import cached_property


class AppliancePluginException(Exception):
    pass


@attr.s(slots=True)
class AppliancePluginDescriptor(object):
    cls = attr.ib()
    args = attr.ib()
    kwargs = attr.ib()
    cache = attr.ib(init=False, default=attr.Factory(dict), repr=False)

    def __get__(self, o, t=None):
        if o is None:
            return self

        if o not in self.cache:
            self.cache[o] = self.cls(o, *self.args, **self.kwargs)

        return self.cache[o]


@attr.s
class AppliancePlugin(object):
    appliance = attr.ib(repr=False)

    @cached_property
    def logger(self):
        # TODO: Change when appliance gets its own
        from utils.log import logger
        return logger

    @classmethod
    def declare(cls, **kwargs):
        return AppliancePluginDescriptor(cls, (), kwargs)
