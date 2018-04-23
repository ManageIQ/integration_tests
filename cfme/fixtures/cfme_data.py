import pytest

from cfme.utils import conf


@pytest.fixture(scope="session")
def cfme_data(request):
    return conf.cfme_data
