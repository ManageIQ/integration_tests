import pytest


@pytest.fixture(scope="function")
def physical_switch(appliance):
    physical_switch = appliance.rest_api.collections.physical_switches[0]
    return physical_switch
