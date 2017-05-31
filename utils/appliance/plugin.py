# -*- coding: utf-8 -*-
import attr
from cached_property import cached_property


class AppliancePluginException(Exception):
    pass


class AppliancePluginDescriptor(object):
    def __init__(self, cls, args, kwargs):
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def __get__(self, o, t=None):
        if o is None:
            return self

        return self.cls(o, *self.args, **self.kwargs)


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
