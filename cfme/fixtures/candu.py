"""
Fixtures for Capacity and Utilization
"""
import pytest


@pytest.fixture(scope="module")
def enable_candu(appliance):
    candu = appliance.collections.candus
    server_settings = appliance.server.settings
    original_roles = server_settings.server_roles_db

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

    yield

    candu.disable_all()
    server_settings.update_server_roles_db(original_roles)
