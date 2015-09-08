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


def test_edit_service_catalog(rest_api):
    """Test editing a service catalog

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        Steps:
        * Retrieve list of entities using GET /api/service_catalogs , pick the first one
        * POST /api/service_catalogs/<id> (method ``edit``) with the ``description``

    Metadata:
        test_flag: rest
    """
    assert "edit" in rest_api.collections.service_catalogs

    try:
        edit_service_catalog = rest_api.collections.templates[0]
    except IndexError:
        pytest.skip("There is no template to be edited")

    new_name = "name_{}".format(fauxfactory.gen_alphanumeric())
    edit_service_catalog.action.edit(name=new_name)
    wait_for(
        lambda: not rest_api.collections.service_catalogs.find_by(
            name=new_name),
        num_sec=180,
        delay=10,
    )


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

    assert "delete" in rest_api.collections.service_catalogs

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

    assert "delete" in rest_api.collections.service_catalogs

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


@pytest.fixture(scope="module")
def users_data():
    name = fauxfactory.gen_alphanumeric()
    users_data = [{
        "name": "name_{}_{}".format(index, name),
        "userid": "userid_{}_{}".format(index, name),
        "email": "{}_{}@local.com".format(index, name),
    } for index in range(1, 5)]

    return users_data


@pytest.fixture(scope="module")
def groups_data():
    name = fauxfactory.gen_alphanumeric()
    groups_data = [{
        "description": "description_{}_{}".format(index, name),
        "miq_user_role_id": index,
    } for index in range(1, 5)]

    return groups_data


@pytest.fixture(scope="module")
def roles_data():
    name = fauxfactory.gen_alphanumeric()
    roles_data = [{
        "name": "name_{}_{}".format(index, name),
        "settings": {
            "restrictions": {
                "vms": "user"
            },
        },
    } for index in range(1, 5)]

    return roles_data


@pytest.fixture(scope="module")
def zones_data():
    name = fauxfactory.gen_alphanumeric()
    zones_data = [{
        "name": "name_{}_{}".format(index, name),
        "description": "description_{}_{}".format(index, name),
    } for index in range(1, 5)]

    return zones_data


@pytest.fixture(scope="module", params=["users", "groups", "roles", "zones"])
def rest_api_access_control(request, rest_api):
    if request.param == 'users':
        return ("users", request.getfuncargvalue("users_data"), rest_api.collections.users)
    elif request.param == 'groups':
        return ("groups", request.getfuncargvalue("groups_data"), rest_api.collections.groups)
    elif request.param == 'roles':
        return ("roles", request.getfuncargvalue("roles_data"), rest_api.collections.roles)
    elif request.param == 'zones':
        return ("zones", request.getfuncargvalue("zones_data"), rest_api.collections.zones)


def test_add_delete_access_control(rest_api_access_control):
    """Tests creating and deleting access control entity: ['users', 'groups', 'roles', 'zones'].

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * access_control = ['users', 'groups', 'roles', 'zones']
        * POST /api/{access_control} (method ``add``)
                for users: ``name``, ```userid`, ``email``
                for groups: ``description``, ``miq_user_role_id``
                for roles: ``name``, ``settings``
        * DELETE /api/{access_control}/<id> -> delete only one entity (not working for zones)
        * DELETE /api/{access_control} <- Insert a JSON with list of dicts containing ``href``s to
            the entity
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.

    Metadata:
        test_flag: rest
    """
    service, entities, api = rest_api_access_control
    assert "delete" in api.action

    for entity in entities:
        api.action.add(entity)

        wait_for(
            lambda: api.find_by(name=entity.get("name")),
            num_sec=180,
            delay=10,
        )

    if service != 'zones':
        delete_entity = api.find_by(name=entities[0].get('name'))
        delete_entity.action.delete()
        wait_for(
            lambda: not api.find_by(name=entities[0].get('name')),
            num_sec=180,
            delay=10,
        )

    entities = [entity.id for entity in api]
    api.delete(entities)
    with error.expected("ActiveRecord::RecordNotFound"):
        api.action.delete(entities)


def test_edit_access_control(rest_api_access_control):
    """Tests editing a access_control entity: ['user', 'group', 'role'].

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * access_control = ['users', 'groups', 'roles']
        * Retrieve list of entities using GET /api/{access_control} , pick the first one
        * POST /api/{access_control}/<id> (method ``edit``) with the ``name``

    Metadata:
        test_flag: rest
    """
    service, entities, api = rest_api_access_control
    assert "edit" in api.action

    try:
        entity = api[0]
    except:
        api.action.add(entities[0])
        entity = api.find_by(name=(entities[0].get('name') or entities[0].get('description')))

    if service == 'groups':
        new_description = "description_{}".format(fauxfactory.gen_alphanumeric())
        entity.action.edit(description=new_description)
        wait_for(
            lambda: api.find_by(description=new_description),
            num_sec=180,
            delay=10,
        )

    new_name = "name_{}".format(fauxfactory.gen_alphanumeric())
    entity.action.edit(name=new_name)
    wait_for(
        lambda: api.find_by(name=new_name),
        num_sec=180,
        delay=10,
    )


@pytest.fixture(scope="module")
def policies_data():
    name = fauxfactory.gen_alphanumeric()
    policies_data = [{
        "description": "description_{}_{}".format(index, name),
        "mode": "compliance",
        "towhat": "Vm",
    } for index in range(1, 5)]

    return policies_data


@pytest.fixture(scope="module")
def policy_profiles_data():
    name = fauxfactory.gen_alphanumeric()
    policy_profiles_data = [{
        "description": "description_{}_{}".format(index, name),
    } for index in range(1, 5)]

    return policy_profiles_data


@pytest.fixture(scope="module")
def added_policies(request, policies_data, rest_api):
    for policy in policies_data:
        rest_api.collections.policies.action.add(policy)
        wait_for(
            lambda: rest_api.collections.policies.find_by(name=policy.get("description")),
            num_sec=180,
            delay=10,
        )

    def fin():
            policies = [policy.id for policy in rest_api.collections.policies]
            rest_api.collections.policies.delete(policies)
    request.addfinalizer(fin)

    return [policy.id for policy in rest_api.collections.policies]


def test_add_delete_policy_profiles(policy_profiles_data, rest_api):
    """Tests creating and deleting policy_profiles

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * POST /api/policy_profiles (method ``add``)
        * DELETE /api/policy_profiles/<id> -> delete only one policy profile
        * DELETE /api/policy_profiles <- Insert a JSON with list of dicts containing ``href``s to
            the policy profile
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.

    Metadata:
        test_flag: rest
    """
    assert "delete" in rest_api.collections.policy_profiles.action

    for policy_profile in policy_profiles_data:
        rest_api.collections.policy_profiles.action.add(policy_profile)

        wait_for(
            lambda: rest_api.collections.policy_profiles.find_by(
                name=policy_profile.get("description")),
            num_sec=180,
            delay=10,
        )

    delete_policy_profile = rest_api.collections.policy_profiles.find_by(
        policy_profiles_data[0].get('description'))
    delete_policy_profile.action.delete()
    wait_for(
        lambda: not rest_api.collections.policy_profiles.find_by(
            name=policy_profiles_data[0].get('description')),
        num_sec=180,
        delay=10,
    )

    policy_profiles = [policy_profile.id for policy_profile in rest_api.collections.policy_profiles]
    rest_api.collections.policy_profiles.delete(policy_profiles)
    with error.expected("ActiveRecord::RecordNotFound"):
        rest_api.collections.policy_profiles.action.delete(policy_profiles)


def test_edit_policy_profile(policy_profiles_data, rest_api):
    """Test editing a policy_profile

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * Retrieve list of entities using GET /api/policy_profiles , pick the first one
        * POST /api/policy_profile/1 (method ``edit``) with the ``description``

    Metadata:
        test_flag: rest
    """
    assert "edit" in rest_api.collections.policy_profiles.action

    try:
        policy_profile = rest_api.collections.policy_profiles[0]
    except:
        rest_api.collections.policy_profiles.action.add(policy_profiles_data[0])
        policy_profile = rest_api.collections.policy_profiles.find_by(
            description=policy_profiles_data[0].get('description'))

    new_description = "description_{}".format(fauxfactory.gen_alphanumeric())

    policy_profile.action.edit(description=new_description)
    wait_for(
        lambda: rest_api.collections.policy_profiles.find_by(description=new_description),
        num_sec=180,
        delay=10,
    )


def test_add_delete_policies_through_profile(added_policies, policy_profiles_data, rest_api):
    """Tests adding a policy_profile with policies and deleting the policies

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * POST /api/policy_profiles (method ``add``)
        * DELETE DELETE /api/policy_profiles/4/policies/24 -> delete only one policy
        * DELETE /api/policy_profiles/<id>/policies <- Insert a JSON with list of dicts containing
          ``href``s to the policies
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.


    Metadata:
        test_flag: rest
    """
    assert "delete" in rest_api.collections.policy_profiles.action

    policy_profile = policy_profiles_data[0]
    policy_profile["policies"] = [{"href": _} for _ in added_policies]
    rest_api.collections.policy_profiles.action.add(policy_profile)
    wait_for(
        lambda: rest_api.collections.policy_profiles.find_by(
            name=policy_profile.get("description")),
        num_sec=180,
        delay=10,
    )

    delete_policy_profile = rest_api.collections.policy_profiles.find_by(
        policy_profile.get("description"))
    delete_policy = delete_policy_profile.policies[0]
    delete_policy.action.delete()
    wait_for(
        lambda: not delete_policy_profile.find_by(name=policy_profile.get("description")),
        num_sec=180,
        delay=10,
    )

    policies = [policy.id for policy in delete_policy_profile.policies]
    rest_api.collections.policy_profiles.delete(policies)
    with error.expected("ActiveRecord::RecordNotFound"):
        rest_api.collections.policy_profiles.action.delete(policies)

    delete_policy_profile.action.delete()
    wait_for(
        lambda: not rest_api.collections.policy_profiles.find_by(
            name=policy_profile.get('description')),
        num_sec=180,
        delay=10,
    )


def test_add_delete_policies(added_policies, rest_api):
    """Tests creating and deleting policies

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * POST /api/policies (method ``add``)
        * DELETE /api/polices/<id> -> delete only one policy
        * DELETE /api/policies <- Insert a JSON with list of dicts containing ``href``s to
            the policy
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.

    Metadata:
        test_flag: rest
    """
    assert "delete" in rest_api.collections.policies.action

    delete_policy = rest_api.collections.policies.find_by(id=added_policies[0])
    delete_policy.action.delete()
    wait_for(
        lambda: not rest_api.collections.policies.find_by(id=added_policies[0]),
        num_sec=180,
        delay=10,
    )

    policies = [policy for policy in rest_api.collections.policies]
    rest_api.collections.policies.delete(policies)
    with error.expected("ActiveRecord::RecordNotFound"):
        rest_api.collections.policies.action.delete(policies)


def test_edit_policy(added_policies, rest_api):
    """Test editing a policy

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * Retrieve list of entities using GET /api/policies , pick the first one
        * POST /api/policies/<id> (method ``edit``) with the ``description``

    Metadata:
        test_flag: rest
    """
    assert "edit" in rest_api.collections.policies.action

    policy = rest_api.collections.policies[0]

    new_description = "description_{}".format(fauxfactory.gen_alphanumeric())

    policy.action.edit(description=new_description)
    wait_for(
        lambda: policy.description == new_description,
        fail_func=policy.reload,
        num_sec=180,
        delay=10,
    )


def test_edit_template(rest_api):
    """Test deleting a template

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        Steps:
        * Retrieve list of entities using GET /api/templates , pick the first one
        * POST /api/templates/<id> (method ``edit``) with the ``description``

    Metadata:
        test_flag: rest
    """
    assert "edit" in rest_api.collections.templates

    try:
        edit_template = rest_api.collections.templates[0]
    except IndexError:
        pytest.skip("There is no template to be edited")

    new_description = "description_{}".format(fauxfactory.gen_alphanumeric())
    edit_template.action.edit(description=new_description)
    wait_for(
        lambda: not rest_api.collections.resource_pools.find_by(
            description=new_description),
        num_sec=180,
        delay=10,
    )


def test_refresh_template(rest_api):
    """Test refreshing a template

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        Steps:
        * Retrieve list of entities using GET /api/policies , pick the first one
        * POST /api/templates/<id> (method ``edit``) with the ``description``

    Metadata:
        test_flag: rest
    """
    assert "refresh" in rest_api.collections.templates

    try:
        template = rest_api.collections.templates[0]
    except IndexError:
        pytest.skip("There is no template to be refreshed")

    old_refresh_dt = template.update_on
    assert template.action.refresh()["success"], "Refresh was unsuccessful"
    wait_for(
        lambda: template.update_on != old_refresh_dt,
        fail_func=template.reload,
        num_sec=180,
        delay=10,
    )


@pytest.fixture(scope="module", params=["resource_pools", "templates", "data_storages",
    "clusters"])
def rest_api_delete_service(request, rest_api):
    if request.param == 'resource_pools':
        return ("resource_pools", rest_api.collections.resource_pools)
    elif request.param == 'templates':
        return ("templates", rest_api.collections.templates)
    elif request.param == 'data_storages':
        return ("data_storages", rest_api.collections.data_storages)
    elif request.param == 'clusters':
        return ("clusters", rest_api.collections.clusters)


def test_delete_service(rest_api_delete_service):
    """Test deleting a service ["resource_pools", "templates", "data_storages", "clusters"]

    Prerequisities:
        * An appliance with ``/api`` available.

    Steps:
        * Retrieve list of entities using GET /api/<service> , pick the first one
        * DELETE /api/<service>/<id> -> delete only one data store
        * DELETE /api/<service> <- Insert a JSON with list of dicts containing ``href``s to
            the services
        * Repeat the DELETE query -> now it should return an ``ActiveRecord::RecordNotFound``.

    Metadata:
        test_flag: rest
    """
    service_name, api_service = rest_api_delete_service
    assert "delete" in api_service

    try:
        delete_service = api_service[0]
    except IndexError:
        pytest.skip("There is no {} to be deleted".format(service_name))

    delete_service.action.delete()
    wait_for(
        lambda: not api_service.find_by(id=delete_service.id),
        num_sec=180,
        delay=10,
    )

    services = [service.id for service in api_service]
    api_service.action.delete(services)
    with error.expected("ActiveRecord::RecordNotFound"):
        api_service.action.delete(services)


COLLECTIONS_IGNORED_53 = {
    "availability_zones", "conditions", "events", "flavors", "policy_actions", "security_groups",
    "tags", "tasks",
}


# TODO: Gradually remove and write separate tests for those when they get extended
@pytest.mark.parametrize(
    "collection_name",
    ["availability_zones", "conditions", "events", "flavors", "policy_actions", "security_groups",
    "tags", "tasks", "request_tasks", "requests", "servers", "service_requests", "zones", "hosts"])
@pytest.mark.uncollectif(lambda collection_name: collection_name in COLLECTIONS_IGNORED_53 and
    current_version() < "5.4")
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
