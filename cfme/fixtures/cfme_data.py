import pytest

from cfme.utils import conf


@pytest.fixture(scope="session")
def cfme_data():
    return conf.cfme_data
