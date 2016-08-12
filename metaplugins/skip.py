# -*- coding: utf-8 -*-
"""I missed callable based skipper so here it is."""
from __future__ import unicode_literals
from markers.meta import plugin

import pytest
from kwargify import kwargify

from utils.pytest_shortcuts import extract_fixtures_values


@plugin("skip", keys=["skip"], run=plugin.BEFORE_RUN)
@plugin("skip", keys=["skip", "reason"], run=plugin.BEFORE_RUN)
def skip_plugin(item, skip, reason="Skipped"):
    if isinstance(skip, bool):
        if skip:
            pytest.skip(reason)
    elif callable(skip):
        skip_kwargified = kwargify(skip)
        if skip_kwargified(**extract_fixtures_values(item)):
            pytest.skip(reason)
    else:
        if bool(skip):
            pytest.skip(reason)
