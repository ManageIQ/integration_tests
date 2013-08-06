import pytest

from common.soap import soap_client as _soap_client

@pytest.fixture()  # IGNORE:E1101
def soap_client(mozwebqa):
    return _soap_client(mozwebqa)

