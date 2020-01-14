# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.common.provider import BaseProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
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
                 ProviderFilter(classes=[SCVMMProvider, RHEVMProvider], inverted=True)],
        scope='module'),
]


@pytest.fixture(scope="module")
def vm_crud(provider, small_template):
    collection = provider.appliance.provider_based_collection(provider)
    return collection.instantiate(random_vm_name(context='genealogy'),
                                  provider,
                                  template_name=small_template.name)


# uncollected above in pytest_generate_tests
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:473"])
@pytest.mark.parametrize("from_edit", [True, False], ids=["via_edit", "via_summary"])
@test_requirements.genealogy
@pytest.mark.uncollectif(
    lambda provider, from_edit: provider.one_of(CloudProvider) and not from_edit)
def test_vm_genealogy_detected(
        request, setup_provider, provider, small_template, soft_assert, from_edit, vm_crud):
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
        assignee: spusaterr
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    vm_crud.create_on_provider(find_in_cfme=True, allow_skip="default")

    request.addfinalizer(lambda: vm_crud.cleanup_on_provider())
    vm_crud.mgmt.wait_for_steady_state()

    if from_edit:
        vm_crud.open_edit()
        view = navigate_to(vm_crud, 'Edit')
        opt = view.form.parent_vm.all_selected_options[0]
        parent = opt.strip()
        assert parent.startswith(small_template.name), "The parent template not detected!"
    else:
        try:
            vm_crud_ancestors = vm_crud.genealogy.ancestors
        except NameError:
            logger.exception("The parent template not detected!")
            raise pytest.fail("The parent template not detected!")
        assert small_template.name in vm_crud_ancestors, \
            "{} is not in {}'s ancestors".format(small_template.name, vm_crud.name)


@pytest.mark.manual
@pytest.mark.tier(1)
@test_requirements.genealogy
def test_compare_button_enabled(provider, appliance, vm_crud):
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


####################################################
    # setup provider
    vm_crud.cleanup_on_provider(find_in_cfme=True, allow_skip="default")



    # establish relationship between VM's

    # navigate to VM summary page

    # Check 2 boxes from tree

    # Verify: Genealogy is set(not null?)
    # Verify: Genealogy summary is displayed
    # Verify: Compare button is enabled
    # Verify: Compare button leads to compare?


@pytest.mark.manual
@test_requirements.genealogy
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

