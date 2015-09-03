# -*- coding: utf-8 -*-
"""This module contains REST API specific tests."""
import fauxfactory
import pytest

from cfme.configure.configuration import server_roles_disabled

from utils import error, mgmt_system, testgen
from utils.providers import setup_a_provider as _setup_a_provider, get_mgmt
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
        rest_api_modscope, provider, small_template):
    templates = rest_api_modscope.collections.templates.find_by(name=small_template)
    for template in templates:
        if template.ems.name == provider.data["name"]:
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
            "vlan": provider.data["provisioning"]["vlan"],
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
    if isinstance(provider.mgmt, mgmt_system.RHEVMSystem):
        result["vm_fields"]["provision_type"] = "native_clone"
    return result


@pytest.mark.meta(server_roles="+automate")
@pytest.mark.usefixtures("setup_provider")
def test_provision(request, provision_data, provider, rest_api):
    """Tests provision via REST API.

    Prerequisities:
        * Have a provider set up with templates suitable for provisioning.

    Steps:
        * POST /api/provision_requests (method ``create``) the JSON with provisioning data. The
            request is returned.
        * Query the request by its id until the state turns to ``finished`` or ``provisioned``.

    Metadata:
        test_flag: rest, provision
    """

    vm_name = provision_data["vm_fields"]["vm_name"]
    request.addfinalizer(
        lambda: provider.mgmt.delete_vm(vm_name) if provider.mgmt.does_vm_exist(vm_name) else None)
    request = rest_api.collections.provision_requests.action.create(**provision_data)[0]

    def _finished():
        request.reload()
        if request.status.lower() in {"error"}:
            pytest.fail("Error when provisioning: `{}`".format(request.message))
        return request.request_state.lower() in {"finished", "provisioned"}

    wait_for(_finished, num_sec=600, delay=5, message="REST provisioning finishes")
    assert provider.mgmt.does_vm_exist(vm_name), "The VM {} does not exist!".format(vm_name)


def test_add_delete_service_catalog(rest_api):
    """Tests creating and deleting a service catalog.

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * POST /api/service_catalogs (method ``add``) with the ``name``, ``description`` and
            ``service_templates`` (empty list)
        * DELETE /api/service_catalogs/<id>
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.

    Metadata:
        test_flag: rest
    """
    scl = rest_api.collections.service_catalogs.action.add(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        service_templates=[]
    )[0]
    scl.action.delete()
    with error.expected("ActiveRecord::RecordNotFound"):
        scl.action.delete()


def test_add_delete_multiple_service_catalogs(rest_api):
    """Tests creating and deleting multiple service catalogs at time.

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * POST /api/service_catalogs (method ``add``) with the list of dictionaries used to create
            the service templates (``name``, ``description`` and ``service_templates``
            (empty list))
        * DELETE /api/service_catalogs <- Insert a JSON with list of dicts containing ``href``s to
            the catalogs
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.

    Metadata:
        test_flag: rest
    """
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


@pytest.mark.ignore_stream("5.3")
def test_provider_refresh(request, setup_a_provider, rest_api):
    """Test checking that refresh invoked from the REST API works.

    It provisions a VM when the Provider inventory functionality is disabled, then the functionality
    is enabled and we wait for refresh to finish by checking the field in provider and then we check
    whether the VM appeared in the provider.

    Prerequisities:
        * A provider that is set up, with templates suitable for provisioning.

    Steps:
        * Disable the ``ems_inventory`` and ``ems_operations`` roles
        * Provision a VM
        * Store old refresh date from the provider
        * Initiate refresh
        * Wait until the refresh date updates
        * The VM should appear soon.

    Metadata:
        test_flag: rest
    """
    if "refresh" not in rest_api.collections.providers.action.all:
        pytest.skip("Refresh action is not implemented in this version")
    provider_mgmt = get_mgmt(setup_a_provider.key)
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
    wait_for(
        lambda: len(rest_api.collections.vms.find_by(name=vm_name)),
        fail_condition=lambda l: l == 0,
        num_sec=180,
        delay=10,
    )
    vms = rest_api.collections.vms.find_by(name=vm_name)
    if "delete" in vms[0].action.all:
        vms[0].action.delete()


@pytest.mark.ignore_stream("5.3")
def test_provider_edit(request, setup_a_provider, rest_api):
    """Test editing a provider using REST API.

    Prerequisities:
        * A provider that is set up. Can be a dummy one.

    Steps:
        * Retrieve list of providers using GET /api/providers , pick the first one
        * POST /api/providers/<id> (method ``edit``) -> {"name": <random name>}
        * Query the provider again. The name should be set.

    Metadata:
        test_flag: rest
    """
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
@pytest.mark.ignore_stream("5.3")
def test_provider_crud(request, rest_api, from_detail):
    """Test the CRUD on provider using REST API.

    Steps:
        * POST /api/providers (method ``create``) <- {"hostname":..., "name":..., "type":
            "EmsVmware"}
        * Remember the provider ID.
        * Delete it either way:
            * DELETE /api/providers/<id>
            * POST /api/providers (method ``delete``) <- list of dicts containing hrefs to the
                providers, in this case just list with one dict.

    Metadata:
        test_flag: rest
    """
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
    provider_mgmt = get_mgmt(setup_a_provider.key)
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
@pytest.mark.ignore_stream("5.3")
def test_set_vm_owner(request, setup_a_provider, rest_api, vm, from_detail):
    """Test whether set_owner action from the REST API works.

    Prerequisities:
        * A VM

    Steps:
        * Find a VM id using REST
        * Call either:
            * POST /api/vms/<id> (method ``set_owner``) <- {"owner": "owner username"}
            * POST /api/vms (method ``set_owner``) <- {"owner": "owner username",
                "resources": [{"href": ...}]}
        * Query the VM again
        * Assert it has the attribute ``evm_owner`` as we set it.

    Metadata:
        test_flag: rest
    """
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
@pytest.mark.ignore_stream("5.3")
def test_vm_add_lifecycle_event(request, setup_a_provider, rest_api, vm, from_detail, db):
    """Test that checks whether adding a lifecycle event using the REST API works.

    Prerequisities:
        * A VM

    Steps:
        * Find the VM's id
        * Prepare the lifecycle event data (``status``, ``message``, ``event``)
        * Call either:
            * POST /api/vms/<id> (method ``add_lifecycle_event``) <- the lifecycle data
            * POST /api/vms (method ``add_lifecycle_event``) <- the lifecycle data + resources field
                specifying list of dicts containing hrefs to the VMs, in this case only one.
        * Verify that appliance's database contains such entries in table ``lifecycle_events``

    Metadata:
        test_flag: rest
    """
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


@pytest.fixture(scope="module")
def user_data():
    name = fauxfactory.gen_alphanumeric()
    result = {
        "name": "name_{}".format(name),
        "userid": "userid_{}".format(name),
        "email": "{}@local.com".format(name),
    }

    return result


def test_add_delete_user(user_data, rest_api):
    """Tests creating and deleting users.

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * POST /api/users (method ``add``) with the ``name``, ``userid`` and ``email``

        * DELETE /api/providers/<id> -> delete only one user
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.

        * DELETE /api/users <- Insert a JSON with list of dicts containing ``href``s to
            the users
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.

    Metadata:
        test_flag: rest
    """
    assert "add" in rest_api.users.action

    users = [{
        "name": "name_{}".format(fauxfactory.gen_alphanumeric()),
        "userid": "userid_{}".format(fauxfactory.gen_alphanumeric()),
        "email": "{}@local.com".format(fauxfactory.gen_alphanumeric()),
    } for _ in range(4)]

    for user in users:
        rest_api.users.action.add(user)

        wait_for(
            lambda: rest_api.users.find_by(name=user.get("name")),
            num_sec=180,
            delay=10,
        )

    delete_user = rest_api.users.find_by(users[0].get('name'))
    delete_user.action.delete()
    wait_for(
        lambda: rest_api.users.find_by(name=users[0].get('name')),
        num_sec=180,
        delay=10,
    )

    rest_api.users.delete(users[1:])
    with error.expected("ActiveRecord::RecordNotFound"):
        rest_api.users.action.delete(users[1:])


def test_edit_user(user_data, rest_api):
    """Tests editing a user.

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * Retrieve list of users using GET /api/users , pick the first one
        * POST /api/users/1 (method ``edit``) with the ``name``

    Metadata:
        test_flag: rest
    """
    assert "edit" in rest_api.users.action

    try:
        user = rest_api.users[0]
    except:
        rest_api.users.action.add(user_data)
        user = rest_api.users.find_by(name=user_data.get('name'))

    new_name = "name_{}".format(fauxfactory.gen_alphanumeric())

    user.action.edit(name=new_name)
    wait_for(
        lambda: rest_api.users.find_by(name=new_name),
        num_sec=180,
        delay=10,
    )


# TODO: Gradually remove and write separate tests for those when they get extended
@pytest.mark.parametrize(
    "collection_name",
    ["availability_zones", "clusters", "conditions", "data_stores", "events", "flavors", "groups",
    "hosts", "policies", "policy_actions", "policy_profiles", "request_tasks", "requests",
    "resource_pools", "roles", "security_groups", "servers", "service_requests", "tags", "tasks",
    "templates", "users", "zones"])
def test_query_simple_collections(rest_api, collection_name):
    """This test tries to load each of the listed collections. 'Simple' collection means that they
    have no usable actions that we could try to run

    Steps:
        * GET /api/<collection_name>

    Metadata:
        test_flag: rest
    """
    if current_version() < "5.4" and collection_name in COLLECTIONS_IGNORED_53:
        pytest.skip("Collection {} not in 5.3.".format(collection_name))
    collection = getattr(rest_api.collections, collection_name)
    collection.reload()
    list(collection)
