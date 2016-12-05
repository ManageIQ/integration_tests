# -*- coding: utf-8 -*-
"""This module contains REST API specific tests."""
import pytest

from cfme import test_requirements
from cfme.rest import vm as _vm
from utils.providers import setup_a_provider as _setup_a_provider
from utils.version import current_version
from utils import testgen, version


pytestmark = [test_requirements.rest]

pytest_generate_tests = testgen.generate(
    testgen.provider_by_type,
    ['virtualcenter', 'rhevm'],
    scope="module"
)


@pytest.fixture(scope="module")
def a_provider():
    return _setup_a_provider("infra")


@pytest.fixture(scope="function")
def vm(request, a_provider, rest_api):
    return _vm(request, a_provider, rest_api)


@pytest.mark.tier(2)
@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_vm_scan(rest_api, vm, from_detail):
    rest_vm = rest_api.collections.vms.get(name=vm)
    if from_detail:
        response = rest_vm.action.scan()
    else:
        response, = rest_api.collections.vms.action.scan(rest_vm)

    @pytest.wait_for(timeout="5m", delay=5, message="REST running scanning vm finishes")
    def _finished():
        response.task.reload()
        if response.task.status.lower() in {"error"}:
            pytest.fail("Error when running scan vm method: `{}`".format(response.task.message))
        return response.task.state.lower() == 'finished'


COLLECTIONS_IGNORED_56 = {
    "arbitration_profiles", "arbitration_rules", "arbitration_settings", "automate",
    "automate_domains", "blueprints", "cloud_networks", "container_deployments", "currencies",
    "measures", "notifications", "orchestration_templates", "virtual_templates",
}


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "collection_name",
    ["arbitration_profiles", "arbitration_rules", "arbitration_settings", "automate",
     "automate_domains", "automation_requests", "availability_zones", "blueprints", "categories",
     "chargebacks", "cloud_networks", "clusters", "conditions", "container_deployments",
     "currencies", "data_stores", "events", "features", "flavors", "groups", "hosts", "instances",
     "measures", "notifications", "orchestration_templates", "pictures", "policies",
     "policy_actions", "policy_profiles", "providers", "provision_dialogs", "provision_requests",
     "rates", "reports", "request_tasks", "requests", "resource_pools", "results", "roles",
     "security_groups", "servers", "service_catalogs", "service_dialogs", "service_orders",
     "service_requests", "service_templates", "services", "tags", "tasks", "templates", "tenants",
     "users", "virtual_templates", "vms", "zones"])
@pytest.mark.uncollectif(
    lambda collection_name: (
        collection_name in COLLECTIONS_IGNORED_56 and current_version() < "5.7"))
def test_query_simple_collections(rest_api, collection_name):
    """This test tries to load each of the listed collections. 'Simple' collection means that they
    have no usable actions that we could try to run
    Steps:
        * GET /api/<collection_name>
    Metadata:
        test_flag: rest
    """
    collection = getattr(rest_api.collections, collection_name)
    collection.reload()
    list(collection)


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_add_picture(rest_api):
    collection = rest_api.collections.pictures
    count = collection.count
    collection.action.create({
        "extension": "png",
        "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcS"
                   "JAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="})
    collection.reload()
    assert collection.count == count + 1


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_http_options(rest_api):
    assert 'boot_time' in rest_api.collections.vms.options()['attributes']


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_server_info(rest_api):
    assert all(item in rest_api.server_info for item in ('appliance', 'build', 'version'))


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_product_info(rest_api):
    assert all(item in rest_api.product_info for item in
               ('copyright', 'name', 'name_full', 'support_website', 'support_website_text'))


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_bulk_query(rest_api):
    entitites = rest_api.collections.events.find_by()
    data0, data1, data2 = entitites[0]._data, entitites[1]._data, entitites[2]._data
    response = rest_api.collections.events.action.query(
        {"id": data0["id"]}, {"href": data1["href"]}, {"href": data2["href"]})
    assert len(response) == 3
    assert data0 == response[0]._data and data1 == response[1]._data and data2 == response[2]._data
