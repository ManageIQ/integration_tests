import fauxfactory
import pytest

from cfme import test_requirements
from cfme.configure.configuration.server_settings import ServerInformation
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import wait_for
from cfme.utils.log import logger
from cfme.utils import error


pytestmark = [test_requirements.rest]


@pytest.fixture(scope='module')
def a_provider(request):
    return _a_provider(request)


@pytest.fixture(scope="function")
def provider_rest(request, appliance):
    response = appliance.rest_api.collections.providers.action.create(
        hostname=fauxfactory.gen_alphanumeric(),
        name=fauxfactory.gen_alphanumeric(),
        type="ManageIQ::Providers::Vmware::InfraManager",
    )
    assert appliance.rest_api.response.status_code == 200
    provider = response[0]

    @request.addfinalizer
    def _finished():
        try:
            appliance.rest_api.collections.providers.action.delete(provider)
        except Exception:
            # provider can be deleted by test
            logger.warning("Failed to delete provider.")

    return provider


@pytest.mark.tier(2)
def test_create_provider(provider_rest):
    """Tests creating provider using REST API.

    Metadata:
        test_flag: rest
    """
    assert provider_rest.type == "ManageIQ::Providers::Vmware::InfraManager"


@pytest.mark.tier(2)
def test_provider_refresh(request, a_provider, appliance):
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
    if "refresh" not in appliance.rest_api.collections.providers.action.all:
        pytest.skip("Refresh action is not implemented in this version")
    provider_rest = appliance.rest_api.collections.providers.get(name=a_provider.name)
    server_settings = ServerInformation(appliance=appliance)
    server_settings.server_roles_disabled("ems_inventory", "ems_operations")
    vm_name = deploy_template(
        a_provider.key,
        "test_rest_prov_refresh_{}".format(fauxfactory.gen_alphanumeric(length=4)))
    request.addfinalizer(lambda: a_provider.mgmt.delete_vm(vm_name))
    provider_rest.reload()
    old_refresh_dt = provider_rest.last_refresh_date
    response = provider_rest.action.refresh()
    assert appliance.rest_api.response.status_code == 200
    assert response["success"], "Refresh was unsuccessful"
    wait_for(
        lambda: provider_rest.last_refresh_date != old_refresh_dt,
        fail_func=provider_rest.reload,
        num_sec=720,
        delay=5,
    )
    # We suppose that thanks to the random string, there will be only one such VM
    wait_for(
        lambda: appliance.rest_api.collections.vms.find_by(name=vm_name) or False,
        num_sec=180,
        delay=10,
    )


@pytest.mark.tier(2)
def test_provider_edit(request, a_provider, appliance):
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
    if "edit" not in appliance.rest_api.collections.providers.action.all:
        pytest.skip("Refresh action is not implemented in this version")
    provider_rest = appliance.rest_api.collections.providers.get(name=a_provider.name)
    new_name = fauxfactory.gen_alphanumeric()
    old_name = provider_rest.name
    request.addfinalizer(lambda: provider_rest.action.edit(name=old_name))
    edited = provider_rest.action.edit(name=new_name)
    assert appliance.rest_api.response.status_code == 200
    provider_rest.reload()
    assert provider_rest.name == new_name == edited.name


@pytest.mark.tier(2)
@pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
def test_provider_delete_from_detail(provider_rest, appliance, method):
    """Tests deletion of the provider from detail using REST API.

    Metadata:
        test_flag: rest
    """
    status = 204 if method == 'delete' else 200
    provider_rest.action.delete(force_method=method)
    assert appliance.rest_api.response.status_code == status
    provider_rest.wait_not_exists(num_sec=30, delay=0.5)
    with error.expected("ActiveRecord::RecordNotFound"):
        provider_rest.action.delete(force_method=method)
    assert appliance.rest_api.response.status_code == 404


@pytest.mark.tier(2)
def test_provider_delete_from_collection(provider_rest, appliance):
    """Tests deletion of the provider from collection using REST API.

    Metadata:
        test_flag: rest
    """
    appliance.rest_api.collections.providers.action.delete(provider_rest)
    assert appliance.rest_api.response.status_code == 200
    provider_rest.wait_not_exists(num_sec=30, delay=0.5)
    with error.expected("ActiveRecord::RecordNotFound"):
        appliance.rest_api.collections.providers.action.delete(provider_rest)
    assert appliance.rest_api.response.status_code == 404
