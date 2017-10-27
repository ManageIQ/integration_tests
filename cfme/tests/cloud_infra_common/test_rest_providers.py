import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.common.provider import CloudInfraProvider
from cfme.utils import error, testgen
from cfme.utils.blockers import BZ
from cfme.utils.rest import assert_response
from cfme.utils.version import pick
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate(classes=[CloudInfraProvider])

pytestmark = [test_requirements.rest]


def delete_provider(appliance, name):
    provs = appliance.rest_api.collections.providers.find_by(name=name)

    if not provs:
        return

    prov = provs[0]

    # workaround for BZ1501941
    def _delete():
        try:
            prov.action.delete()
        except Exception as exc:
            if 'ActiveRecord::RecordNotFound' in str(exc):
                return True
            raise
        retval = prov.wait_not_exists(num_sec=20, silent_failure=True)
        return bool(retval)

    if appliance.version >= '5.9' and BZ(1501941, forced_streams=['5.9', 'upstream']).blocks:
        prov.action.edit(enabled=False)
        wait_for(_delete, num_sec=80)
    else:
        prov.action.delete()
        prov.wait_not_exists(num_sec=30)


@pytest.fixture(scope="function")
def provider_rest(request, appliance, provider):
    """Creates provider using REST API."""
    delete_provider(appliance, provider.name)
    request.addfinalizer(lambda: delete_provider(appliance, provider.name))

    default_connection = {
        "endpoint": {"role": "default"}
    }
    con_config_to_include = []

    # provider attributes
    prov_data = {
        "hostname": provider.hostname,
        "ipaddress": provider.ip_address,
        "name": provider.name,
        "type": "ManageIQ::Providers::{}".format(provider.db_types[0]),
    }

    if hasattr(provider, "region"):
        prov_data["provider_region"] = pick(
            provider.region) if isinstance(provider.region, dict) else provider.region
    if hasattr(provider, "project"):
        prov_data["project"] = provider.project

    if provider.one_of(AzureProvider):
        prov_data["uid_ems"] = provider.tenant_id
        prov_data["provider_region"] = provider.region.lower().replace(" ", "")
        if hasattr(provider, "subscription_id"):
            prov_data["subscription"] = provider.subscription_id

    # default endpoint
    endpoint_default = provider.endpoints["default"]
    if hasattr(endpoint_default.credentials, "principal"):
        prov_data["credentials"] = {
            "userid": endpoint_default.credentials.principal,
            "password": endpoint_default.credentials.secret,
        }
    elif hasattr(endpoint_default.credentials, "service_account"):
        default_connection["authentication"] = {
            "type": "AuthToken",
            "auth_type": "default",
            "auth_key": endpoint_default.credentials.service_account,
        }
        con_config_to_include.append(default_connection)
    else:
        pytest.skip("No credentials info found for provider {}.".format(provider.name))

    cert = getattr(endpoint_default, "ca_certs", None)
    if cert:
        default_connection["endpoint"]["certificate_authority"] = cert
        con_config_to_include.append(default_connection)

    if hasattr(endpoint_default, "verify_tls"):
        default_connection["endpoint"]["verify_ssl"] = 1 if endpoint_default.verify_tls else 0
        con_config_to_include.append(default_connection)
    if hasattr(endpoint_default, "api_port") and endpoint_default.api_port:
        default_connection["endpoint"]["port"] = endpoint_default.api_port
        con_config_to_include.append(default_connection)
    if hasattr(endpoint_default, "security_protocol") and endpoint_default.security_protocol:
        security_protocol = endpoint_default.security_protocol.lower()
        if security_protocol == "basic (ssl)":
            security_protocol = "ssl"
        default_connection["endpoint"]["security_protocol"] = security_protocol
        con_config_to_include.append(default_connection)

    # candu endpoint
    if "candu" in provider.endpoints:
        endpoint_candu = provider.endpoints["candu"]
        if isinstance(prov_data["credentials"], dict):
            prov_data["credentials"] = [prov_data["credentials"]]
        prov_data["credentials"].append({
            "userid": endpoint_candu.credentials.principal,
            "password": endpoint_candu.credentials.secret,
            "auth_type": "metrics",
        })
        candu_connection = {
            "endpoint": {
                "hostname": endpoint_candu.hostname,
                "path": endpoint_candu.database,
                "role": "metrics",
            },
        }
        if hasattr(endpoint_candu, "api_port") and endpoint_candu.api_port:
            candu_connection["endpoint"]["port"] = endpoint_candu.api_port
        if hasattr(endpoint_candu, "verify_tls") and not endpoint_candu.verify_tls:
            candu_connection["endpoint"]["verify_ssl"] = 0
        con_config_to_include.append(candu_connection)

    prov_data["connection_configurations"] = []
    appended = []
    for config in con_config_to_include:
        role = config["endpoint"]["role"]
        if role not in appended:
            prov_data["connection_configurations"].append(config)
            appended.append(role)

    response = appliance.rest_api.collections.providers.action.create(**prov_data)
    assert_response(appliance)

    provider_rest = response[0]
    return provider_rest


@pytest.mark.tier(1)
def test_create_provider(provider_rest):
    """Tests creating provider using REST API.

    Metadata:
        test_flag: rest
    """
    assert "ManageIQ::Providers::" in provider_rest.type


@pytest.mark.tier(1)
def test_provider_refresh(provider_rest, appliance, provider):
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


@pytest.mark.tier(1)
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


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1501941, forced_streams=['5.9', 'upstream'])])
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
    assert_response(appliance)
    provider_rest.wait_not_exists(num_sec=30)
    with error.expected("ActiveRecord::RecordNotFound"):
        del_action()
    assert_response(appliance, http_status=404)


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1501941, forced_streams=['5.9', 'upstream'])])
def test_provider_delete_from_collection(provider_rest, appliance):
    """Tests deletion of the provider from collection using REST API.

    Metadata:
        test_flag: rest
    """
    appliance.rest_api.collections.providers.action.delete(provider_rest)
    assert_response(appliance)
    provider_rest.wait_not_exists(num_sec=30)
    with error.expected("ActiveRecord::RecordNotFound"):
        appliance.rest_api.collections.providers.action.delete(provider_rest)
    assert_response(appliance, http_status=404)
