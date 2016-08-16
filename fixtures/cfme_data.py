from __future__ import unicode_literals
import pytest

from utils import conf


@pytest.fixture(scope="session")
def cfme_data(request):
    return conf.cfme_data
