# -*- coding: utf-8 -*-
import pytest

from cfme.common.vm import VM
from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
import cfme.fixtures.pytest_selenium as sel
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.common.provider import BaseProvider
from cfme.utils.providers import ProviderFilter
from markers.env_markers.provider import providers


pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers', 'provider'),
    pytest.mark.tier(2),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[BaseProvider]),
                                  lambda provider: not provider.one_of(SCVMMProvider,
                                                                       RHEVMProvider)],
                         scope='module'),
]


@pytest.fixture(scope="function")
def vm_crud(provider, small_template):
    return VM.factory(random_vm_name(context='genealogy'), provider,
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
    """
    vm_crud.create_on_provider(find_in_cfme=True, allow_skip="default")

    @request.addfinalizer
    def _():
        if provider.mgmt.does_vm_exist(vm_crud.name):
            provider.mgmt.delete_vm(vm_crud.name)
    provider.mgmt.wait_vm_steady(vm_crud.name)

    if from_edit:
        vm_crud.open_edit()
        opt = vm_crud.edit_form.parent_sel.first_selected_option
        if isinstance(opt, tuple):
            # AngularSelect
            parent = opt.text.strip()
        else:
            # Ordinary Select
            parent = sel.text(opt).strip()
        assert parent.startswith(small_template.name), "The parent template not detected!"
    else:
        try:
            vm_crud_ancestors = vm_crud.genealogy.ancestors
        except NameError:
            logger.exception("The parent template not detected!")
            raise pytest.fail("The parent template not detected!")
        assert small_template.name in vm_crud_ancestors, \
            "{} is not in {}'s ancestors".format(small_template.name, vm_crud.name)
