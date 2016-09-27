# -*- coding: utf-8 -*-
"""This module contains REST API specific tests."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme import Credential
from cfme.configure.access_control import User, Group
from cfme.login import login, login_admin
from cfme.rest import vm as _vm
from utils.providers import setup_a_provider as _setup_a_provider
from utils.version import current_version
from utils import testgen, conf, version


pytestmark = [test_requirements.rest]

pytest_generate_tests = testgen.generate(
    testgen.provider_by_type,
    ['virtualcenter', 'rhevm'],
    scope="module"
)


@pytest.fixture(scope="module")
def a_provider():
    return _setup_a_provider("infra")


@pytest.fixture(scope='function')
def user():
    user = User(credential=Credential(principal=fauxfactory.gen_alphanumeric(),
        secret=fauxfactory.gen_alphanumeric()), name=fauxfactory.gen_alphanumeric(),
        group=Group(description='EvmGroup-super_administrator'))
    user.create()
    return user


# This test should be deleted when we get new build > 5.5.2.4
@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
def test_edit_user_password(request, rest_api, user):
    if "edit" not in rest_api.collections.users.action.all:
        pytest.skip("Edit action for users is not implemented in this version")
    request.addfinalizer(login_admin)
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


COLLECTIONS_IGNORED_53 = {
    "availability_zones", "conditions", "events", "flavors", "policy_actions", "security_groups",
    "tags", "tasks",
}

COLLECTIONS_IGNORED_54 = {
    "features", "pictures", "provision_dialogs", "rates", "results", "service_dialogs",
}


@pytest.mark.tier(3)
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
