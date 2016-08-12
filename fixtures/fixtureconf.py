from __future__ import unicode_literals
import pytest


@pytest.fixture
def fixtureconf(request):
    """Provides easy access to the fixtureconf dict in fixtures"""
    return request.node._fixtureconf
