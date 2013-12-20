import pytest

import utils.soap


@pytest.fixture()  # IGNORE:E1101
def soap_client():
    return utils.soap.soap_client()
