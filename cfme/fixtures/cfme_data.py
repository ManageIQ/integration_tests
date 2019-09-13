import pytest

from cfme.utils.config_data import cfme_data as data


@pytest.fixture(scope="session")
def cfme_data(request):
    return data
