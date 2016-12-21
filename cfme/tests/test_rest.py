# -*- coding: utf-8 -*-
"""This module contains REST API specific tests."""
import pytest
import fauxfactory
import utils.error as error

from cfme import test_requirements
from cfme.rest import vm as _vm
from cfme.rest import arbitration_settings as _arbitration_settings
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
def test_identity(rest_api):
    """Check that user's identity is returned.

    Metadata:
        test_flag: rest
    """
    assert all(item in rest_api.identity for item in
               ('userid', 'name', 'group', 'role', 'tenant', 'groups'))


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_user_settings(rest_api):
    """Check that user's settings are returned.

    Metadata:
        test_flag: rest
    """
    assert isinstance(rest_api.settings, dict)


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_bulk_query(rest_api):
    """Tests bulk query referencing resources by attributes id, href and guid

    Metadata:
        test_flag: rest
    """
    collection = rest_api.collections.events
    data0, data1, data2 = collection[0]._data, collection[1]._data, collection[2]._data
    response = rest_api.collections.events.action.query(
        {"id": data0["id"]}, {"href": data1["href"]}, {"guid": data2["guid"]})
    assert len(response) == 3
    assert data0 == response[0]._data and data1 == response[1]._data and data2 == response[2]._data


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_bulk_query_users(rest_api):
    """Tests bulk query on 'users' collection

    Metadata:
        test_flag: rest
    """
    data = rest_api.collections.users[0]._data
    response = rest_api.collections.users.action.query(
        {"name": data["name"]}, {"userid": data["userid"]})
    assert len(response) == 2
    assert data["id"] == response[0]._data["id"] == response[1]._data["id"]


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_bulk_query_roles(rest_api):
    """Tests bulk query on 'roles' collection

    Metadata:
        test_flag: rest
    """
    collection = rest_api.collections.roles
    data0, data1 = collection[0]._data, collection[1]._data
    response = rest_api.collections.roles.action.query(
        {"name": data0["name"]}, {"name": data1["name"]})
    assert len(response) == 2
    assert data0 == response[0]._data and data1 == response[1]._data


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_bulk_query_groups(rest_api):
    """Tests bulk query on 'groups' collection

    Metadata:
        test_flag: rest
    """
    collection = rest_api.collections.groups
    data0, data1 = collection[0]._data, collection[1]._data
    response = rest_api.collections.groups.action.query(
        {"description": data0["description"]}, {"description": data1["description"]})
    assert len(response) == 2
    assert data0 == response[0]._data and data1 == response[1]._data


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_create_arbitration_settings(request, rest_api):
    """Tests create arbitration_settings

    Metadata:
        test_flag: rest
    """
    response = _arbitration_settings(request, rest_api, num=2)
    collection = rest_api.collections.arbitration_settings
    record = collection.get(id=response[0].id)
    assert len(response) == 2
    assert record._data == response[0]._data


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_delete_arbitration_settings(request, rest_api, from_detail):
    """Tests delete arbitration_settings

    Metadata:
        test_flag: rest
    """
    response = _arbitration_settings(request, rest_api, num=2)
    collection = rest_api.collections.arbitration_settings
    if from_detail:
        methods = ['post', 'delete']
        for i, ent in enumerate(response):
            ent.action.delete(force_method=methods[i % 2])
            with error.expected("ActiveRecord::RecordNotFound"):
                ent.action.delete()
    else:
        collection.action.delete(*response)
        with error.expected("ActiveRecord::RecordNotFound"):
            collection.action.delete(*response)


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_edit_arbitration_settings(request, rest_api, from_detail):
    """Tests edit arbitration_settings

    Metadata:
        test_flag: rest
    """
    num_settings = 2
    response = _arbitration_settings(request, rest_api, num=num_settings)
    uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_settings)]
    new = [{'name': 'test_edit{}'.format(u), 'display_name': 'Test Edit{}'.format(u)} for u in uniq]
    if from_detail:
        edited = []
        for i, _ in enumerate(response):
            edited.append(response[i].action.edit(**new[i]))
    else:
        for i, _ in enumerate(response):
            new[i].update(response[i]._ref_repr())
        edited = rest_api.collections.arbitration_settings.action.edit(*new)
    for i, _ in enumerate(edited):
        assert edited[i].name == new[i]['name'] and edited[i].display_name == new[i]['display_name']
