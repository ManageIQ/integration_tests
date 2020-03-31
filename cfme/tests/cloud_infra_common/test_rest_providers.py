import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import query_resource_attributes
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.rest,
    pytest.mark.tier(1),
    pytest.mark.provider([CloudProvider, InfraProvider])
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


def test_query_provider_attributes(provider, provider_rest, soft_assert):
    """Tests access to attributes of /api/providers.

    Metadata:
        test_flag: rest

    Bugzilla:
        1612905
        1546112

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/30h
    """
    outcome = query_resource_attributes(provider_rest)
    for failure in outcome.failed:
        # once BZ1546112 is fixed other failure than internal server error is expected
        soft_assert(False, '{} "{}": status: {}, error: `{}`'.format(
            failure.type, failure.name, failure.response.status_code, failure.error))


def test_provider_options(appliance):
    """Tests that provider settings are present in OPTIONS listing.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    options = appliance.rest_api.options(appliance.rest_api.collections.providers._href)
    assert 'provider_settings' in options['data']


def test_create_provider(provider_rest):
    """Tests creating provider using REST API.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    assert "ManageIQ::Providers::" in provider_rest.type


def test_provider_refresh(provider_rest, appliance):
    """Test checking that refresh invoked from the REST API works.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
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
        assert task.status.lower() == "ok", f"Task failed with status '{task.status}'"


def test_provider_edit(request, provider_rest, appliance):
    """Test editing a provider using REST API.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    new_name = fauxfactory.gen_alphanumeric()
    old_name = provider_rest.name
    request.addfinalizer(lambda: provider_rest.action.edit(name=old_name))
    edited = provider_rest.action.edit(name=new_name)
    assert_response(appliance)
    provider_rest.reload()
    assert provider_rest.name == new_name == edited.name


@pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
def test_provider_delete_from_detail(provider_rest, method):
    """Tests deletion of the provider from detail using REST API.

    Bugzilla:
        1525498
        1501941

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    delete_resources_from_detail([provider_rest], method=method, num_sec=50)


def test_provider_delete_from_collection(provider_rest):
    """Tests deletion of the provider from collection using REST API.

    Bugzilla:
        1525498
        1501941

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    delete_resources_from_collection([provider_rest], num_sec=50)


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1656502])
@pytest.mark.provider([RHEVMProvider], selector=ONE, required_flags=["metrics_collection"])
def test_create_rhev_provider_with_metric(setup_provider, provider):
    """
    Bugzilla:
        1656502

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/10h
        testSteps:
            1. Add rhv provider with metrics via REST
        expectedResults:
            1. Provider must be added with all the details provided.
                In this case metric data. no data should be missing.
    """
    navigate_to(provider, "Edit")
    view = provider.create_view(provider.endpoints_form)
    assert view.candu.hostname.read() == provider.endpoints["candu"].hostname
