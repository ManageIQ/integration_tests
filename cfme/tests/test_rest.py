# -*- coding: utf-8 -*-
"""This module contains REST API specific tests."""
import fauxfactory
import pytest

from cfme import Credential
from cfme.configure.access_control import User, Group
from cfme.configure.configuration import server_roles_disabled
from cfme.login import login
from utils.providers import setup_a_provider as _setup_a_provider
from utils.version import current_version
from utils.virtual_machines import deploy_template
from utils.wait import wait_for
from utils import mgmt_system, testgen, conf, version


pytest_generate_tests = testgen.generate(
    testgen.provider_by_type,
    ['virtualcenter', 'rhevm'],
    "small_template",
    scope="module"
)

pytestmark = [pytest.mark.ignore_stream("5.3")]


@pytest.fixture(scope="module")
def a_provider():
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


@pytest.mark.usefixtures("logged_in")
@pytest.fixture(scope='function')
def user():
    user = User(credential=Credential(principal=fauxfactory.gen_alphanumeric(),
        secret=fauxfactory.gen_alphanumeric()), name=fauxfactory.gen_alphanumeric(),
        group=Group(description='EvmGroup-super_administrator'))
    user.create()
    return user


@pytest.fixture(scope='function')
def automation_requests_data():
    return [{
        "uri_parts": {
            "namespace": "System",
            "class": "Request",
            "instance": "InspectME",
            "message": "create",
        },
        "parameters": {
            "vm_name": "test_rest_{}".format(fauxfactory.gen_alphanumeric()),
            "vm_memory": 4096,
            "memory_limit": 16384,
        },
        "requester": {
            "auto_approve": True
        }
    } for index in range(1, 5)]


# Here also available the ability to create multiple provision request, but used the save
# href and method, so it doesn't make any sense actually
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


def test_provider_refresh(request, a_provider, rest_api):
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
    provider_rest = rest_api.collections.providers.get(name=a_provider.name)
    with server_roles_disabled("ems_inventory", "ems_operations"):
        vm_name = deploy_template(
            a_provider.key,
            "test_rest_prov_refresh_{}".format(fauxfactory.gen_alphanumeric(length=4)))
        request.addfinalizer(lambda: a_provider.mgmt.delete_vm(vm_name))
    provider_rest.reload()
    old_refresh_dt = provider_rest.last_refresh_date
    assert provider_rest.action.refresh()["success"], "Refresh was unsuccessful"
    wait_for(
        lambda: provider_rest.last_refresh_date,
        fail_func=provider_rest.reload,
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
    vm = rest_api.collections.vms.get(name=vm_name)
    if "delete" in vm.action.all:
        vm.action.delete()


def test_provider_edit(request, a_provider, rest_api):
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
    provider_rest = rest_api.collections.providers[0]
    new_name = fauxfactory.gen_alphanumeric()
    old_name = provider_rest.name
    request.addfinalizer(lambda: provider_rest.action.edit(name=old_name))
    provider_rest.action.edit(name=new_name)
    provider_rest.reload()
    assert provider_rest.name == new_name


@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["delete_from_detail", "delete_from_collection"])
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
        pytest.skip("Create action is not implemented in this version")

    if current_version() < "5.5":
        provider_type = "EmsVmware"
    else:
        provider_type = "ManageIQ::Providers::Vmware::InfraManager"
    provider = rest_api.collections.providers.action.create(
        hostname=fauxfactory.gen_alphanumeric(),
        name=fauxfactory.gen_alphanumeric(),
        type=provider_type,
    )[0]
    if from_detail:
        provider.action.delete()
        provider.wait_not_exists(num_sec=30, delay=0.5)
    else:
        rest_api.collections.providers.action.delete(provider)
        provider.wait_not_exists(num_sec=30, delay=0.5)


@pytest.fixture(scope="module")
def vm(request, a_provider, rest_api):
    if "refresh" not in rest_api.collections.providers.action.all:
        pytest.skip("Refresh action is not implemented in this version")
    provider_rest = rest_api.collections.providers.get(name=a_provider.name)
    vm_name = deploy_template(
        a_provider.key,
        "test_rest_vm_{}".format(fauxfactory.gen_alphanumeric(length=4)))
    request.addfinalizer(lambda: a_provider.mgmt.delete_vm(vm_name))
    provider_rest.action.refresh()
    wait_for(
        lambda: len(rest_api.collections.vms.find_by(name=vm_name)) > 0,
        num_sec=600, delay=5)
    return vm_name


@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_set_vm_owner(request, rest_api, vm, from_detail):
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
    rest_vm = rest_api.collections.vms.get(name=vm)
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
def test_vm_add_lifecycle_event(request, rest_api, vm, from_detail, db):
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
    rest_vm = rest_api.collections.vms.get(name=vm)
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


@pytest.mark.parametrize(
    "multiple", [False, True],
    ids=["one_request", "multiple_requests"])
def test_automation_requests(request, rest_api, automation_requests_data, multiple):
    """Test adding the automation request
     Prerequisities:
        * An appliance with ``/api`` available.
    Steps:
        * POST /api/automation_request - (method ``create``) add request
        * Retrieve list of entities using GET /api/automation_request and find just added request
    Metadata:
        test_flag: rest, requests
    """

    if "automation_requests" not in rest_api.collections:
        pytest.skip("automation request collection is not implemented in this version")

    if multiple:
        requests = rest_api.collections.automation_requests.action.create(*automation_requests_data)
    else:
        requests = rest_api.collections.automation_requests.action.create(
            automation_requests_data[0])

    def _finished():
        for request in requests:
            request.reload()
            if request.status.lower() not in {"error"}:
                return False
        return True

    wait_for(_finished, num_sec=600, delay=5, message="REST automation_request finishes")


@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
def test_edit_user_password(rest_api, user):
    if "edit" not in rest_api.collections.users.action.all:
        pytest.skip("Edit action for users is not implemented in this version")
    try:
        for cur_user in rest_api.collections.users:
            if cur_user.userid != conf.credentials['default']['username']:
                rest_user = cur_user
                break
    except:
        pytest.skip("There is no user to change password")

    new_password = fauxfactory.gen_alphanumeric()
    rest_user.action.edit(password=new_password)
    cred = Credential(principal=rest_user.userid, secret=new_password)
    new_user = User(credential=cred)
    login(new_user)


@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
def test_set_service_owner(rest_api, services):
    if "set_ownership" not in rest_api.collections.services.action.all:
        pytest.skip("Set owner action for service is not implemented in this version")
    service = services[0]
    user = rest_api.collections.users.get(userid='admin')
    data = {
        "owner": {"href": user.href}
    }
    service.action.set_ownership(data)
    service.reload()
    assert hasattr(service, "evm_owner")
    assert service.evm_owner.userid == user.userid


@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
def test_set_services_owner(rest_api, services):
    if "set_ownership" not in rest_api.collections.services.action.all:
        pytest.skip("Set owner action for service is not implemented in this version")
    data = []
    for service in services:
        tmp_data = {
            "href": service.href,
            "owner": {"href": user.href}
        }
        data.append(tmp_data)
    rest_api.collections.services.action.set_ownership(*data)
    for service in services:
        service.reload()
        assert hasattr(service, "evm_owner")
        assert service.evm_owner.userid == user.userid


@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_vm_add_event(rest_api, vm, db, from_detail):
    event = {
        "event_type": "BadUserNameSessionEvent",
        "event_message": "Cannot login user@test.domain {}".format(from_detail)
    }
    rest_vm = rest_api.collections.vms.get(name=vm)
    if from_detail:
        assert rest_vm.action.add_event(event)["success"], "Could not add event"
    else:
        response = rest_api.collections.vms.action.add_event(rest_vm, **event)
        assert (len(response) > 0, "Could not add event")

    # DB check, doesn't work on 5.4
    if version.current_version() < '5.5':
        return True
    events = db["event_streams"]
    events_list = list(db.session.query(events).filter(
        events.vm_name == vm,
        events.message == event["event_message"],
        events.event_type == event["event_type"],
    ))
    assert(len(events_list) == 1, "Could not find the event in the database")


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
            pytest.fail("Error when running report: `{}`".format(response.task.message))
        return response.task.state.lower() == 'finished'


COLLECTIONS_IGNORED_53 = {
    "availability_zones", "conditions", "events", "flavors", "policy_actions", "security_groups",
    "tags", "tasks",
}

COLLECTIONS_IGNORED_54 = {
    "features", "pictures", "provision_dialogs", "rates", "results", "service_dialogs",
}


@pytest.mark.parametrize(
    "collection_name",
    ["availability_zones", "chargebacks", "clusters", "conditions", "data_stores", "events",
    "features", "flavors", "groups", "hosts", "pictures", "policies", "policy_actions",
    "policy_profiles", "provision_dialogs", "rates", "request_tasks", "requests", "resource_pools",
    "results", "roles", "security_groups", "servers", "service_dialogs", "service_requests",
    "tags", "tasks", "templates", "users", "vms", "zones"])
@pytest.mark.uncollectif(
    lambda collection_name: (
        collection_name in COLLECTIONS_IGNORED_53 and current_version() < "5.4") or (
            collection_name in COLLECTIONS_IGNORED_54 and current_version() < "5.5"))
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
