import pytest


@pytest.fixture(scope="function")
def physical_switch(appliance, provider, setup_provider):
    try:
        physical_switch = appliance.rest_api.collections.physical_switches.filter(
            {"provider": provider}
        ).all()[0]
    except IndexError:
        pytest.skip('No physical switch on provider')
    return physical_switch
