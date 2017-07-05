# -*- coding: utf-8 -*-
from __future__ import absolute_import
from widgetastic.utils import ParametrizedLocator
from widgetastic_patternfly import BootstrapSelect


class BootstrapSelectByLocator(BootstrapSelect):
    """Modified :py:class:`widgetastic_patternfly.BootstrapSelect` that uses the div locator."""
    ROOT = ParametrizedLocator('{@locator}')

    def __init__(self, parent, locator, can_hide_on_select=False, logger=None):
        BootstrapSelect.__init__(self, parent, locator, can_hide_on_select, logger)
        self.locator = locator
