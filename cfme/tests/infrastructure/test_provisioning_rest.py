import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.wait import wait_for
from cfme.utils import testgen
from cfme.utils.version import current_version


pytestmark = [test_requirements.provision]

pytest_generate_tests = testgen.generate([VMwareProvider, RHEVMProvider], scope="module")


def get_provision_data(rest_api, provider, template_name, auto_approve=True):
    templates = rest_api.collections.templates.find_by(name=template_name)
    for template in templates:
        try:
            ems_id = template.ems_id
        except AttributeError:
            continue
        if ems_id == provider.id:
            guid = template.guid
            break
    else:
        raise Exception("No such template {} on provider!".format(template_name))

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
            "auto_approve": auto_approve
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

    if provider.one_of(RHEVMProvider):
        result["vm_fields"]["provision_type"] = "native_clone"
    return result


@pytest.fixture(scope="module")
def provision_data(appliance, provider, small_template_modscope):
    return get_provision_data(appliance.rest_api, provider, small_template_modscope.name)


# Here also available the ability to create multiple provision request, but used the save
# href and method, so it doesn't make any sense actually
@pytest.mark.tier(2)
@pytest.mark.meta(server_roles="+automate")
@pytest.mark.usefixtures("setup_provider")
def test_provision(request, provision_data, provider, appliance):
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
    response = appliance.rest_api.collections.provision_requests.action.create(**provision_data)
    assert appliance.rest_api.response.status_code == 200
    provision_request = response[0]

    def _finished():
        provision_request.reload()
        if "error" in provision_request.status.lower():
            pytest.fail("Error when provisioning: `{}`".format(provision_request.message))
        return provision_request.request_state.lower() in ("finished", "provisioned")

    wait_for(_finished, num_sec=800, delay=5, message="REST provisioning finishes")
    assert provider.mgmt.does_vm_exist(vm_name), "The VM {} does not exist!".format(vm_name)


@pytest.mark.tier(2)
@pytest.mark.meta(server_roles="+automate")
@pytest.mark.usefixtures("setup_provider")
def test_create_pending_provision_requests(appliance, provider, small_template):
    """Tests creation and and auto-approval of pending provision request
    using /api/provision_requests.

    Metadata:
        test_flag: rest, provision
    """
    provision_data = get_provision_data(
        appliance.rest_api, provider, small_template.name, auto_approve=False)
    response = appliance.rest_api.collections.provision_requests.action.create(**provision_data)
    assert appliance.rest_api.response.status_code == 200
    # check that the `approval_state` is pending_approval
    for prov_request in response:
        assert prov_request.options['auto_approve'] is False
        assert prov_request.approval_state == 'pending_approval'
    # The Automate approval process is running as part of the request workflow.
    # The request is within the specified parameters so it shall be auto-approved.
    for prov_request in response:
        prov_request.reload()
        wait_for(
            lambda: prov_request.approval_state == 'approved',
            fail_func=prov_request.reload,
            num_sec=300,
            delay=10)


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.tier(2)
@pytest.mark.meta(server_roles="+automate")
@pytest.mark.usefixtures("setup_provider")
def test_provision_attributes(appliance, provider, small_template):
    """Tests that it's possible to display additional attributes in /api/provision_requests/:id.

    Metadata:
        test_flag: rest, provision
    """
    provision_data = get_provision_data(
        appliance.rest_api, provider, small_template.name, auto_approve=False)
    response = appliance.rest_api.collections.provision_requests.action.create(**provision_data)
    assert appliance.rest_api.response.status_code == 200
    provision_request = response[0]
    # workaround for BZ1437689 to make sure the vm is not provisioned
    provision_request.action.deny(reason="denied")
    provision_request.reload(attributes=('v_workflow_class', 'v_allowed_tags'))
    assert provision_request.v_workflow_class
    assert provision_request.v_allowed_tags
