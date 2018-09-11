import pytest
from wrapanapi import VmState

from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.virtual_machines import deploy_template

pytestmark = [
    pytest.mark.provider([InfraProvider])
]


@pytest.fixture(scope="module")
def vm_crud(provider):
    collection = provider.appliance.provider_based_collection(provider)
    vm_name = random_vm_name(context='pblsh')
    vm = collection.instantiate(vm_name, provider)
    deploy_template(vm.provider.key, vm_name, provider.data['small_template'],
                    timeout=2500)
    vm.wait_to_appear(timeout=900, load_details=False)
    yield vm

    try:
        vm.cleanup_on_provider()
    except Exception:
        logger.exception('Exception deleting test vm "%s" on %s', vm.name,
                         provider.name)


@pytest.mark.rhv2
@pytest.mark.provider([RHEVMProvider], override=True, scope="module",
                      required_fields=[['templates', 'small_template']],
                      selector=ONE_PER_TYPE)
@pytest.mark.meta(blockers=[BZ(1622952, forced_streams=['5.10'])])
def test_publish_vm_to_template(request, setup_provider, vm_crud):
    """ Try to publish VM to template.
    Steps:
        1) Deploy a VM and make sure it is stopped, otherwise Publish button isn't available
        2) Publish the VM to a template
        3) Check that the template exists

    """
    vm_crud.mgmt.ensure_state(VmState.STOPPED)
    vm_crud.refresh_relationships()

    template_name = random_vm_name(context='pblsh')
    template = vm_crud.publish_to_template(template_name)

    request.addfinalizer(template.delete)

    assert template.exists, 'Published template does not exist.'
