import pytest

from cfme.fixtures.provider import setup_or_skip


@pytest.fixture(scope="function")
def migration_ui(appliance):
    """Fixture to enable migration UI"""
    appliance.enable_migration_ui()
    yield
    appliance.disable_migration_ui()


@pytest.fixture(scope='function')
def v2v_providers(request, migration_ui, second_provider, provider):
    """ Fixture to setup providers """
    setup_or_skip(request, second_provider)
    setup_or_skip(request, provider)
    yield second_provider, provider
    second_provider.delete_if_exists(cancel=False)
    provider.delete_if_exists(cancel=False)


@pytest.fixture(scope='function')
def host_creds(v2v_providers):
    """Add credentials to conversation host"""
    provider = v2v_providers[0]
    host = provider.hosts.all()[0]
    host_data, = [data for data in provider.data['hosts'] if data['name'] == host.name]
    host.update_credentials_rest(credentials=host_data['credentials'])
    yield host
    host.remove_credentials_rest()


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
