import pytest


@pytest.fixture(scope='function')
def dashboards(appliance):
    return appliance.collections.dashboards


@pytest.fixture(scope="function")
def objects(appliance):
    return appliance.collections.object_store_objects
