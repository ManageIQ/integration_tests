# -*- coding: utf-8 -*-
"""I missed callable based skipper so here it is."""
from markers.meta import plugin

import pytest


@plugin("skip", keys=["skip"])
@plugin("skip", keys=["skip", "reason"])
def skip_plugin(skip, reason="Skipped"):
    if isinstance(skip, bool):
        if skip:
            pytest.skip(reason)
    elif callable(skip):
        if skip():
            pytest.skip(reason)
    else:
        if bool(skip):
            pytest.skip(reason)
