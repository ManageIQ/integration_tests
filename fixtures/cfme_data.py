from __future__ import absolute_import
import pytest

from utils import conf


@pytest.fixture(scope="session")
def cfme_data(request):
    return conf.cfme_data
