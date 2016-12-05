# -*- coding: utf-8 -*-
"""REST API specific automate tests."""
import pytest

from cfme import test_requirements
from utils import version


pytestmark = [test_requirements.rest]


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_rest_search_automate(rest_api):
    auto = rest_api.collections.automate
    more_depth = auto.query_string(depth="2")
    full_depth = auto.query_string(depth="-1")
    search = auto.query_string(depth="-1", search_options="state_machines")
    assert len(full_depth) > len(more_depth) > len(auto) and len(full_depth) > len(search) > 0
