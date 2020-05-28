import fauxfactory
import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.common.provider import BaseProvider
from cfme.containers.provider.openshift import OpenshiftProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter

pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers', 'provider'),
    pytest.mark.tier(2),
    pytest.mark.provider(
        gen_func=providers,
        filters=[ProviderFilter(classes=[BaseProvider]),
                 ProviderFilter(classes=[SCVMMProvider, RHEVMProvider, OpenshiftProvider],
                                inverted=True)],
        scope='module'),
    test_requirements.genealogy
]


@pytest.fixture
def create_vm_with_clone(request, create_vm, provider, appliance):
    """Fixture to provision a VM and clone it"""
    first_name = fauxfactory.gen_alphanumeric()
    last_name = fauxfactory.gen_alphanumeric()
    email = "{first_name}.{last_name}@test.com"
    provision_type = 'VMware'

    vm_name = random_vm_name(context=None, max_length=15)

    create_vm.clone_vm(email, first_name, last_name, vm_name, provision_type)
    vm2 = appliance.collections.infra_vms.instantiate(vm_name, provider)
    wait_for(lambda: vm2.exists, timeout=10)

    @request.addfinalizer
    def _cleanup():
        vm2.cleanup_on_provider()
        provider.refresh_provider_relationships()

    return create_vm, vm2

# uncollected above in pytest_generate_tests
@pytest.mark.parametrize("from_edit", [True, False], ids=["via_edit", "via_summary"])
@pytest.mark.uncollectif(lambda provider, from_edit:
                         provider.one_of(CloudProvider) and not from_edit,
                         reason='Cloud provider genealogy only shown on edit')
@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_vm_genealogy_detected(
        request, setup_provider, provider, small_template, soft_assert, from_edit, create_vm):
    """Tests vm genealogy from what CFME can detect.

    Prerequisities:
        * A provider that is set up and having suitable templates for provisioning.

    Steps:
        * Provision the VM
        * Then, depending on whether you want to check it via ``Genealogy`` or edit page:
            * Open the edit page of the VM and you can see the parent template in the dropdown.
                Assert that it corresponds with the template the VM was deployed from.
            * Open VM Genealogy via details page and see the the template being an ancestor of the
                VM.

    Note:
        The cloud providers appear to not have Genealogy option available in the details view. So
        the only possibility available is to do the check via edit form.

    Metadata:
        test_flag: genealogy, provision

    Polarion:
        assignee: spusater
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    if from_edit:
        create_vm.open_edit()
        view = navigate_to(create_vm, 'Edit')
        opt = view.form.parent_vm.all_selected_options[0]
        parent = opt.strip()
        assert parent.startswith(small_template.name), "The parent template not detected!"
    else:
        try:
            vm_crud_ancestors = create_vm.genealogy.ancestors
        except NameError:
            logger.exception("The parent template not detected!")
            pytest.fail("The parent template not detected!")
        assert small_template.name in vm_crud_ancestors, \
            f"{small_template.name} is not in {create_vm.name}'s ancestors"


@pytest.mark.provider([VMwareProvider])
@pytest.mark.tier(1)
def test_compare_button_enabled(create_vm_with_clone, soft_assert):
    """
    Test that compare button is enabled

    Polarion:
        assignee: spusater
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.10.4
        setup:
            1. Have a provider with some VMs added
        testSteps:
            1. Set the parent-child relationship for at least two VMs
            2. Open one of the VM's genealogy screen from its summary
            3. Check at least two checkboxes in the genealogy tree
        expectedResults:
            1. Genealogy set
            2. Genealogy screen displayed
            3. Compare button enabled
    Bugzilla:
        1694712
    """
    assert create_vm_with_clone[0].genealogy.compare(*create_vm_with_clone).is_displayed


@pytest.mark.manual
@pytest.mark.tier(2)
def test_cloud_infra_genealogy():
    """
    Edit infra vm and cloud instance
    When editing cloud instance, genealogy should be present on the edit
    page.
    When you have two providers - one infra and one cloud - added, there
    should be no cloud vms displayed when setting genealogy for infra vm
    and vice-versa.

    Polarion:
        assignee: spusater
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
        setup: Have a cloud instance and an infra vm
        testSteps:
            1. Navigate to instance/vm details, choose Genealogy
            2. Verify that for cloud instance no infra vms are displayed
            3. Verify that for infra vm no cloud instances are displayed
        expectedResults:
            1. Genealogy displayed
            2. No infra vms displayed
            3. No cloud instances displayed
    Bugzilla:
        1399141
        1399144
    """
    pass
