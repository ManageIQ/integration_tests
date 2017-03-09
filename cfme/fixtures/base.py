import pytest
from utils.appliance import get_or_create_current_appliance


@pytest.fixture(scope="session")
def appliance():
    return get_or_create_current_appliance()
