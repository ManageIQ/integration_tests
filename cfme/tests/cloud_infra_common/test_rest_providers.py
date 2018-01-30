import fauxfactory
import pytest

from cfme import test_requirements
from cfme.common.provider import CloudInfraProvider
from cfme.utils import error
from cfme.utils.rest import assert_response, delete_resources_from_collection
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.rest,
    pytest.mark.tier(1),
    pytest.mark.provider([CloudInfraProvider])
]


def delete_provider(appliance, name):
    provs = appliance.rest_api.collections.providers.find_by(name=name)

    if not provs:
        return

    prov = provs[0]

    prov.action.delete()
    prov.wait_not_exists()


@pytest.fixture(scope="function")
def provider_rest(request, appliance, provider):
    """Creates provider using REST API."""
    delete_provider(appliance, provider.name)
    request.addfinalizer(lambda: delete_provider(appliance, provider.name))

    provider.create_rest()
    assert_response(appliance)

    provider_rest = appliance.rest_api.collections.providers.get(name=provider.name)
    return provider_rest


def test_create_provider(provider_rest):
    """Tests creating provider using REST API.

    Metadata:
        test_flag: rest
    """
    assert "ManageIQ::Providers::" in provider_rest.type


def test_provider_refresh(provider_rest, appliance):
    """Test checking that refresh invoked from the REST API works.

    Metadata:
        test_flag: rest
    """
    # initiate refresh
    def _refresh_success():
        provider_rest.action.refresh()
        # the provider might not be ready yet, wait a bit
        if "failed last authentication check" in appliance.rest_api.response.json()["message"]:
            return False
        return True

    if not wait_for(_refresh_success, num_sec=30, delay=2, silent_failure=True):
        pytest.fail("Authentication failed, check credentials.")
    task_id = appliance.rest_api.response.json().get("task_id")
    assert_response(appliance, task_wait=0)

    # wait for an acceptable task state
    if task_id:
        task = appliance.rest_api.get_entity("tasks", task_id)
        wait_for(
            lambda: task.state.lower() in ("finished", "queued"),
            fail_func=task.reload,
            num_sec=30,
        )
        assert task.status.lower() == "ok", "Task failed with status '{}'".format(task.status)


def test_provider_edit(request, provider_rest, appliance):
    """Test editing a provider using REST API.

    Metadata:
        test_flag: rest
    """
    new_name = fauxfactory.gen_alphanumeric()
    old_name = provider_rest.name
    request.addfinalizer(lambda: provider_rest.action.edit(name=old_name))
    edited = provider_rest.action.edit(name=new_name)
    assert_response(appliance)
    provider_rest.reload()
    assert provider_rest.name == new_name == edited.name


# testing BZ1501941
@pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
def test_provider_delete_from_detail(provider_rest, appliance, method):
    """Tests deletion of the provider from detail using REST API.

    Metadata:
        test_flag: rest
    """
    if method == "delete":
        del_action = provider_rest.action.delete.DELETE
    else:
        del_action = provider_rest.action.delete.POST

    del_action()
    # testing BZ1525498
    assert_response(appliance)
    provider_rest.wait_not_exists(num_sec=50)
    with error.expected("ActiveRecord::RecordNotFound"):
        del_action()
    assert_response(appliance, http_status=404)


# testing BZ1501941
def test_provider_delete_from_collection(provider_rest, appliance):
    """Tests deletion of the provider from collection using REST API.

    Metadata:
        test_flag: rest
    """
    collection = appliance.rest_api.collections.providers
    # testing BZ1525498
    delete_resources_from_collection(collection, [provider_rest], num_sec=50)
