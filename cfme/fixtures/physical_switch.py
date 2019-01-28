import pytest


@pytest.fixture(scope="function")
def physical_switch(appliance, provider, setup_provider):
    try:
        physical_switch = appliance.rest_api.collectiions.physical_switches.filter(
            {"provider": provider}
        ).all()[0]
    except IndexError:
        pytest.skip('No physical switch on provider')
    except AttributeError:
        pytest.skip('No physical switches in rest API collection')
    return physical_switch
