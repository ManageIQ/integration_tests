from contextlib import contextmanager

import pytest

from cfme.test_framework.sprout.client import SproutClient


@contextmanager
def _temp_appliance():
    sprout_client = SproutClient.from_config()
    apps, request_id = sprout_client.provision_appliances(preconfigured=True)
    app = apps[0]
    app.stop_evm_service()
    app.extend_db_partition()
    app.start_evm_service()
    yield app
    sprout_client.destroy_pool(request_id)


@pytest.yield_fixture(scope="module")
def temp_appliance(temp_appliance_modscope):
    yield temp_appliance_modscope


@pytest.yield_fixture(scope="module")
def temp_appliance_modscope():
    with _temp_appliance() as appliance:
        yield appliance


@pytest.yield_fixture(scope="class")
def temp_appliance_clsscope():
    with _temp_appliance() as appliance:
        yield appliance


@pytest.yield_fixture(scope="function")
def temp_appliance_funcscope():
    with _temp_appliance() as appliance:
        yield appliance
