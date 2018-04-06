"""
Fixtures for Capacity and Utilization
"""
import pytest
from cfme.common.provider import BaseProvider
from fixtures.provider import setup_or_skip


@pytest.yield_fixture(scope="module")
def enable_candu(appliance):
    candu = appliance.collections.candus
    server_settings = appliance.server.settings
    original_roles = server_settings.server_roles_db
    try:
        server_settings.enable_server_roles(
            'ems_metrics_coordinator',
            'ems_metrics_collector',
            'ems_metrics_processor'
        )
        server_settings.disable_server_roles(
            'automate',
            'smartstate'
        )
        candu.enable_all()

        # ToDo: Its temporary wait for the metric collection.
        # It should replace by wait_for with proper condition depends on the provider.
        import time
        time.sleep(900)
        yield
    finally:
        candu.disable_all()
        server_settings.update_server_roles_db(original_roles)


@pytest.yield_fixture(scope="module")
def clean_setup_provider(request, provider):
    BaseProvider.clear_providers()
    setup_or_skip(request, provider)
    yield
    BaseProvider.clear_providers()
