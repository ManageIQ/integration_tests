from __future__ import unicode_literals
import pytest

import utils.soap


@pytest.fixture()  # IGNORE:E1101
def soap_client(uses_soap):
    return utils.soap.soap_client()
