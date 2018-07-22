import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.blockers import BZ
from cfme.utils.rest import assert_response, query_resource_attributes
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.provision,
    pytest.mark.tier(2),
    pytest.mark.meta(server_roles='+automate'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope='module')
]


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
        raise Exception('No such template {} on provider!'.format(template_name))

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
            "request_id": "1001",
            "placement_auto": "true"
        },
        "ems_custom_attributes": {},
        "miq_custom_attributes": {}
    }

    if provider.one_of(RHEVMProvider):
        result['vm_fields']['provision_type'] = 'native_clone'
        if provider.appliance.version > '5.9.0.16':
            result['vm_fields']['vlan'] = '<Template>'

    return result


@pytest.fixture(scope='function')
def provision_data(appliance, provider, small_template_modscope):
    return get_provision_data(appliance.rest_api, provider, small_template_modscope.name)


def clean_vm(appliance, provider, vm_name):
    found_vms = appliance.rest_api.collections.vms.find_by(name=vm_name)
    if found_vms:
        vm = found_vms[0]
        vm.action.delete()
        vm.wait_not_exists(num_sec=15, delay=2)
    appliance.collections.infra_vms.instantiate(vm_name, provider).cleanup_on_provider()


@pytest.mark.rhv2
# Here also available the ability to create multiple provision request, but used the save
# href and method, so it doesn't make any sense actually
def test_provision(request, appliance, provider, provision_data):
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
    vm_name = provision_data['vm_fields']['vm_name']
    request.addfinalizer(lambda: clean_vm(appliance, provider, vm_name))
    appliance.rest_api.collections.provision_requests.action.create(**provision_data)
    assert_response(appliance)
    provision_request = appliance.collections.requests.instantiate(description=vm_name,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Provisioning failed with the message {}".format(
        provision_request.rest.message)
    assert provision_request.is_succeeded(), msg
    found_vms = appliance.rest_api.collections.vms.find_by(name=vm_name)
    assert found_vms, 'VM `{}` not found'.format(vm_name)


@pytest.mark.rhv3
@pytest.mark.meta(server_roles="+notifier")
def test_provision_emails(request, provision_data, provider, appliance, smtp_test):
    """
    Test that redundant e-mails are not received when provisioning VM that has some
    attributes set to values that differ from template's default.

    Metadata:
        test_flag: rest, provision
    """
    def check_one_approval_mail_received():
        return len(smtp_test.get_emails(
            subject_like="%%Your Virtual Machine configuration was Approved%%")) == 1

    def check_one_completed_mail_received():
        return len(smtp_test.get_emails(
            subject_like="%%Your virtual machine request has Completed%%")) == 1

    request.addfinalizer(lambda: clean_vm(appliance, provider, vm_name))

    vm_name = provision_data["vm_fields"]["vm_name"]
    memory = int(provision_data["vm_fields"]["vm_memory"])
    provision_data["vm_fields"]["vm_memory"] = str(memory / 2)
    provision_data["vm_fields"]["number_of_cpus"] += 1

    appliance.rest_api.collections.provision_requests.action.create(**provision_data)
    assert_response(appliance)

    request = appliance.collections.requests.instantiate(description=vm_name, partial_check=True)
    request.wait_for_request()
    assert provider.mgmt.does_vm_exist(vm_name), "The VM {} does not exist!".format(vm_name)

    wait_for(check_one_approval_mail_received, num_sec=90, delay=5)
    wait_for(check_one_completed_mail_received, num_sec=90, delay=5)


@pytest.mark.rhv3
def test_create_pending_provision_requests(request, appliance, provider, small_template):
    """Tests creation and and auto-approval of pending provision request
    using /api/provision_requests.

    Metadata:
        test_flag: rest, provision
    """
    provision_data = get_provision_data(
        appliance.rest_api, provider, small_template.name, auto_approve=False)
    vm_name = provision_data['vm_fields']['vm_name']
    request.addfinalizer(lambda: clean_vm(appliance, provider, vm_name))
    prov_request, = appliance.rest_api.collections.provision_requests.action.create(
        **provision_data)
    assert_response(appliance)
    # check that the `approval_state` is pending_approval
    assert prov_request.options['auto_approve'] is False
    assert prov_request.approval_state == 'pending_approval'
    # The Automate approval process is running as part of the request workflow.
    # The request is within the specified parameters so it shall be auto-approved.
    prov_request.reload()
    wait_for(
        lambda: prov_request.approval_state == 'approved',
        fail_func=prov_request.reload,
        num_sec=300,
        delay=10)
    # Wait for provisioning to finish
    wait_for(
        lambda: prov_request.request_state == 'finished',
        fail_func=prov_request.reload,
        num_sec=600,
        delay=10)


@pytest.mark.rhv3
@pytest.mark.meta(blockers=[BZ(1592326, forced_streams=['5.8', '5.9', '5.10'])])
def test_provision_attributes(appliance, provider, small_template, soft_assert):
    """Tests that it's possible to display additional attributes in /api/provision_requests/:id.

    Metadata:
        test_flag: rest, provision
    """
    provision_data = get_provision_data(
        appliance.rest_api, provider, small_template.name, auto_approve=False)
    provision_request, = appliance.rest_api.collections.provision_requests.action.create(
        **provision_data)
    assert_response(appliance)
    # workaround for BZ1437689 to make sure the vm is not provisioned
    provision_request.action.deny(reason='denied')
    query_resource_attributes(provision_request, soft_assert=soft_assert)
