import pytest

from cfme.fixtures.provider import setup_or_skip
from cfme.utils.hosts import setup_host_creds


@pytest.fixture(scope="function")
def migration_ui(appliance):
    """Fixture to enable migration UI"""
    appliance.enable_migration_ui()
    yield
    appliance.disable_migration_ui()


@pytest.fixture(scope='function')
def provider_setup(migration_ui, request, second_provider, provider):
    """Fixture to setup nvc and rhv provider"""
    setup_or_skip(request, second_provider)
    setup_or_skip(request, provider)
    yield second_provider, provider
    second_provider.delete_if_exists(cancel=False)
    provider.delete_if_exists(cancel=False)


@pytest.fixture(scope='function')
def host_creds(provider_setup):
    """Add credentials to conversation host"""
    host = provider_setup[0].hosts[0]
    setup_host_creds(provider_setup[0], host.name)
    yield host
    setup_host_creds(provider_setup[0], host.name, remove_creds=True)


@pytest.fixture(scope='function')
def conversion_tags(appliance, host_creds):
    """Assigning tags to conversation host"""
    tag1 = appliance.collections.categories.instantiate(
        display_name='V2V - Transformation Host *').collections.tags.instantiate(
        display_name='t')
    tag2 = appliance.collections.categories.instantiate(
        display_name='V2V - Transformation Method').collections.tags.instantiate(
        display_name='VDDK')
    host_creds.add_tags(tags=(tag1, tag2))
    yield
    host_creds.remove_tags(tags=(tag1, tag2))
