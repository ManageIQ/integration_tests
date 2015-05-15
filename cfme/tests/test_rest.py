# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration import server_roles_disabled

from utils import error, mgmt_system, testgen
from utils.providers import setup_a_provider as _setup_a_provider, provider_factory
from utils.version import current_version
from utils.virtual_machines import deploy_template
from utils.wait import wait_for

pytest_generate_tests = testgen.generate(
    testgen.provider_by_type,
    ['virtualcenter', 'rhevm'],
    "small_template",
    scope="module"
)

pytestmark = [pytest.mark.ignore_stream("5.2")]


@pytest.fixture(scope="module")
def setup_a_provider():
    return _setup_a_provider("infra")


@pytest.fixture(scope="module")
def provision_data(
        rest_api_modscope, provider_crud, provider_key, provider_data, small_template,
        provider_mgmt):
    templates = rest_api_modscope.collections.templates.find_by(name=small_template)
    for template in templates:
        if template.ems.name == provider_data["name"]:
            guid = template.guid
            break
    else:
        raise Exception("No such template {} on provider!".format(small_template))
    result = {
        "version": "1.1",
        "template_fields": {
            "guid": guid
        },
        "vm_fields": {
            "number_of_cpus": 1,
            "vm_name": "test_rest_prov_{}".format(fauxfactory.gen_alphanumeric()),
            "vm_memory": "2048",
            "vlan": provider_data["provisioning"]["vlan"],
        },
        "requester": {
            "user_name": "admin",
            "owner_first_name": "John",
            "owner_last_name": "Doe",
            "owner_email": "jdoe@sample.com",
            "auto_approve": True
        },
        "tags": {
            "network_location": "Internal",
            "cc": "001"
        },
        "additional_values": {
            "request_id": "1001"
        },
        "ems_custom_attributes": {},
        "miq_custom_attributes": {}
    }
    if isinstance(provider_mgmt, mgmt_system.RHEVMSystem):
        result["vm_fields"]["provision_type"] = "native_clone"
    return result


@pytest.mark.meta(server_roles="+automate")
@pytest.mark.usefixtures("setup_provider")
def test_provision(request, provision_data, provider_mgmt, rest_api):
    """Tests provision via rest

    Metadata:
        test_flag: rest, provision
    """

    vm_name = provision_data["vm_fields"]["vm_name"]
    request.addfinalizer(
        lambda: provider_mgmt.delete_vm(vm_name) if provider_mgmt.does_vm_exist(vm_name) else None)
    request = rest_api.collections.provision_requests.action.create(**provision_data)[0]

    def _finished():
        request.reload()
        if request.status.lower() in {"error"}:
            pytest.fail("Error when provisioning: `{}`".format(request.message))
        return request.request_state.lower() in {"finished", "provisioned"}

    wait_for(_finished, num_sec=600, delay=5, message="REST provisioning finishes")
    assert provider_mgmt.does_vm_exist(vm_name), "The VM {} does not exist!".format(vm_name)


def test_add_delete_service_catalog(rest_api):
    scl = rest_api.collections.service_catalogs.action.add(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        service_templates=[]
    )[0]
    scl.action.delete()
    with error.expected("ActiveRecord::RecordNotFound"):
        scl.action.delete()


def test_add_delete_multiple_service_catalogs(rest_api):
    def _gen_ctl():
        return {
            "name": fauxfactory.gen_alphanumeric(),
            "description": fauxfactory.gen_alphanumeric(),
            "service_templates": []
        }
    scls = rest_api.collections.service_catalogs.action.add(
        *[_gen_ctl() for _ in range(4)]
    )
    rest_api.collections.service_catalogs.action.delete(*scls)
    with error.expected("ActiveRecord::RecordNotFound"):
        rest_api.collections.service_catalogs.action.delete(*scls)


def test_provider_refresh(request, setup_a_provider, rest_api):
    """Test checking that refresh invoked from the REST API works.

    It provisions a VM when the Provider inventory functionality is disabled, then the functionality
    is enabled and we wait for refresh to finish by checking the field in provider and then we check
    whether the VM appeared in the provider.
    """
    if "refresh" not in rest_api.collections.providers.action.all:
        pytest.skip("Refresh action is not implemented in this version")
    provider_mgmt = provider_factory(setup_a_provider.key)
    provider = rest_api.collections.providers.find_by(name=setup_a_provider.name)[0]
    with server_roles_disabled("ems_inventory", "ems_operations"):
        vm_name = deploy_template(
            setup_a_provider.key,
            "test_rest_prov_refresh_{}".format(fauxfactory.gen_alphanumeric(length=4)))
        request.addfinalizer(lambda: provider_mgmt.delete_vm(vm_name))
    provider.reload()
    old_refresh_dt = provider.last_refresh_date
    assert provider.action.refresh()["success"], "Refresh was unsuccessful"
    wait_for(
        lambda: provider.last_refresh_date,
        fail_func=provider.reload,
        fail_condition=lambda refresh_date: refresh_date == old_refresh_dt,
        num_sec=720,
        delay=5,
    )
    # We suppose that thanks to the random string, there will be only one such VM
    vms = rest_api.collections.vms.find_by(name=vm_name)
    assert len(vms) > 0, "Could not find the VM {}".format(vm_name)
    if "delete" in vms[0].action.all:
        vms[0].action.delete()


def test_provider_edit(request, setup_a_provider, rest_api):
    if "edit" not in rest_api.collections.providers.action.all:
        pytest.skip("Refresh action is not implemented in this version")
    provider = rest_api.collections.providers[0]
    new_name = fauxfactory.gen_alphanumeric()
    old_name = provider.name
    request.addfinalizer(lambda: provider.action.edit(name=old_name))
    provider.action.edit(name=new_name)
    provider.reload()
    assert provider.name == new_name


@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["delete_from_detail", "delete_from_collection"])
def test_provider_crud(request, rest_api, from_detail):
    if "create" not in rest_api.collections.providers.action.all:
        pytest.skip("Refresh action is not implemented in this version")
    provider = rest_api.collections.providers.action.create(
        hostname=fauxfactory.gen_alphanumeric(),
        name=fauxfactory.gen_alphanumeric(),
        type="EmsVmware",
    )[0]
    if from_detail:
        provider.action.delete()
        provider.wait_not_exists(num_sec=30, delay=0.5)
    else:
        rest_api.collections.providers.action.delete(provider)
        provider.wait_not_exists(num_sec=30, delay=0.5)


@pytest.fixture(scope="module")
def vm(request, setup_a_provider, rest_api):
    if "refresh" not in rest_api.collections.providers.action.all:
        pytest.skip("Refresh action is not implemented in this version")
    provider_mgmt = provider_factory(setup_a_provider.key)
    provider = rest_api.collections.providers.find_by(name=setup_a_provider.name)[0]
    vm_name = deploy_template(
        setup_a_provider.key,
        "test_rest_vm_{}".format(fauxfactory.gen_alphanumeric(length=4)))
    request.addfinalizer(lambda: provider_mgmt.delete_vm(vm_name))
    provider.action.refresh()
    wait_for(
        lambda: len(rest_api.collections.vms.find_by(name=vm_name)) > 0,
        num_sec=600, delay=5)
    return vm_name


@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_set_vm_owner(request, setup_a_provider, rest_api, vm, from_detail):
    """Test whether set_owner action from the REST API works."""
    if "set_owner" not in rest_api.collections.vms.action.all:
        pytest.skip("Set owner action is not implemented in this version")
    rest_vm = rest_api.collections.vms.find_by(name=vm)[0]
    if from_detail:
        assert rest_vm.action.set_owner(owner="admin")["success"], "Could not set owner"
    else:
        assert (
            len(rest_api.collections.vms.action.set_owner(rest_vm, owner="admin")) > 0,
            "Could not set owner")
    rest_vm.reload()
    assert hasattr(rest_vm, "evm_owner")
    assert rest_vm.evm_owner.userid == "admin"


@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_vm_add_lifecycle_event(request, setup_a_provider, rest_api, vm, from_detail, db):
    if "add_lifecycle_event" not in rest_api.collections.vms.action.all:
        pytest.skip("add_lifecycle_event action is not implemented in this version")
    rest_vm = rest_api.collections.vms.find_by(name=vm)[0]
    event = dict(
        status=fauxfactory.gen_alphanumeric(),
        message=fauxfactory.gen_alphanumeric(),
        event=fauxfactory.gen_alphanumeric(),
    )
    if from_detail:
        assert rest_vm.action.add_lifecycle_event(**event)["success"], "Could not add event"
    else:
        assert (
            len(rest_api.collections.vms.action.add_lifecycle_event(rest_vm, **event)) > 0,
            "Could not add event")
    # DB check
    lifecycle_events = db["lifecycle_events"]
    assert len(list(db.session.query(lifecycle_events).filter(
        lifecycle_events.message == event["message"],
        lifecycle_events.status == event["status"],
        lifecycle_events.event == event["event"],
    ))) == 1, "Could not find the lifecycle event in the database"


COLLECTIONS_IGNORED_53 = {
    "availability_zones", "conditions", "events", "flavors", "policy_actions", "security_groups",
    "tags", "tasks",
}


# TODO: Gradually remove and write separate tests for those when they get extended
@pytest.mark.parametrize(
    "collection_name",
    ["availability_zones", "clusters", "conditions", "data_stores", "events", "flavors", "groups",
    "hosts", "policies", "policy_actions", "policy_profiles", "request_tasks", "requests",
    "resource_pools", "roles", "security_groups", "servers", "service_requests", "tags", "tasks",
    "templates", "users", "zones"])
def test_query_simple_collections(rest_api, collection_name):
    """This test tries to load each of the listed collections. 'Simple' collection means that they
    have no usable actions that we could try to run"""
    if current_version() < "5.4" and collection_name in COLLECTIONS_IGNORED_53:
        pytest.skip("Collection {} not in 5.3.".format(collection_name))
    collection = getattr(rest_api.collections, collection_name)
    collection.reload()
    list(collection)
