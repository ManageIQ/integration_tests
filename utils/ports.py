# -*- coding: utf-8 -*-
"""Storage for ports. Set defaults here, then :py:mod:`fixtures.portset` will make overrides."""
import sys

from fixtures.pytest_store import store
from utils.log import logger


class Ports(object):
    def __init__(self):
        self.store = store
        self.logger = logger
        # Port that is used to used for SSH connections to an appliance
        self.SSH = 22
        # POrt that is used to connect to the POstgreSQL database of the appliance.
        self.DB = 5432

    def __setattr__(self, attr, value):
        super(self.__class__, self).__setattr__(attr, value)
        if self.store.any_appliance:
            self.logger.info("Invalidating lazy_cache ssh_client current_appliance object")
            del(self.store.current_appliance.ssh_client)


sys.modules[__name__] = Ports()
