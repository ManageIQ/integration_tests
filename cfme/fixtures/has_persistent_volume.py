import pytest


@pytest.fixture(scope='function')
def has_persistent_volume(provider, appliance):
    """Verifying that some persistent volume exists"""
    vols = provider.mgmt.list_persistent_volume()
    vols_count = len(vols)
    if vols_count:
        yield
    else:
        pytest.skip(f'No Persistent Volumes Detected on OpenShift Provider {provider.name}')
