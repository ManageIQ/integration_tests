import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.virtual_machines import deploy_template

pytestmark = [
    pytest.mark.provider([InfraProvider],
    required_fields=[['templates', 'small_template'],
                    ['provisioning', 'template'],
                    ['provisioning', 'host'],
                    ['provisioning', 'datastore']]),
    test_requirements.vmware,
    test_requirements.rhev
]


@pytest.fixture(scope="module")
def vm_crud(provider):
    collection = provider.appliance.provider_based_collection(provider)
    vm_name = random_vm_name(context='pblsh')
    vm = collection.instantiate(vm_name, provider)
    try:
        deploy_template(vm.provider.key, vm_name,
            provider.data.templates.small_template.name, timeout=2500)
    except (KeyError, AttributeError):
        pytest.skip("Skipping as small_template could not be found on the provider")
    vm.wait_to_appear(timeout=900, load_details=False)
    yield vm

    try:
        vm.cleanup_on_provider()
    except Exception:
        logger.exception('Exception deleting test vm "%s" on %s', vm.name,
                         provider.name)


@pytest.mark.rhv2
@pytest.mark.provider([RHEVMProvider, VMwareProvider], override=True, scope="module",
                      required_fields=[['templates', 'small_template']],
                      selector=ONE_PER_TYPE)
def test_publish_vm_to_template(request, setup_provider, vm_crud):
    """ Try to publish VM to template.
    Steps:
        1) Deploy a VM and make sure it is stopped, otherwise Publish button isn't available
        2) Publish the VM to a template
        3) Check that the template exists


    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Provisioning
    """
    vm_crud.mgmt.ensure_state(VmState.STOPPED)
    vm_crud.refresh_relationships()

    template_name = random_vm_name(context='pblsh')
    template = vm_crud.publish_to_template(template_name)

    @request.addfinalizer
    def _cleanup():
        template.delete()
        # also delete the template from the provider
        template.mgmt.delete()

    assert template.exists, 'Published template does not exist.'
