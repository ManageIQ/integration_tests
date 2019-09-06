import pytest

from cfme.utils.conf import cfme_data

CONFIG_MANAGERS = [cfg_mgr_key for cfg_mgr_key in cfme_data.get('configuration_managers', {})]


@pytest.fixture(params=CONFIG_MANAGERS)
def config_manager_obj(request, appliance):
    collection = "satellite_providers"
    if "ansible" in request.param:
        collection = "ansible_tower_providers"

    yield getattr(appliance.collections, collection).instantiate(key=request.param)


@pytest.fixture(scope="module", params=CONFIG_MANAGERS)
def config_manager_obj_module_scope(request, appliance):
    collection = "satellite_providers"
    if "ansible" in request.param:
        collection = "ansible_tower_providers"

    yield getattr(appliance.collections, collection).instantiate(key=request.param)


@pytest.fixture(scope="class", params=CONFIG_MANAGERS)
def config_manager_obj_class_scope(request, appliance):
    collection = "satellite_providers"
    if "ansible" in request.param:
        collection = "ansible_tower_providers"

    yield getattr(appliance.collections, collection).instantiate(key=request.param)
