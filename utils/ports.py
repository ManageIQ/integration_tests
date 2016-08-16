# -*- coding: utf-8 -*-
"""Storage for ports. Set defaults here, then :py:mod:`fixtures.portset` will make overrides."""
from __future__ import unicode_literals
import sys

from utils.log import logger
from utils import clear_property_cache


class Ports(object):

    SSH = 22
    DB = 5432
    logger = logger

    @property
    def _top(self, m=sys.modules):
        mod = m.get('utils.appliance')

        return mod and mod.stack.top

    def __setattr__(self, attr, value):
        super(self.__class__, self).__setattr__(attr, value)
        if self._top is not None:
            self.logger.info("Invalidating lazy_cache ssh_client current_appliance object")
            clear_property_cache(self._top, 'ssh_client')


sys.modules[__name__] = Ports()
