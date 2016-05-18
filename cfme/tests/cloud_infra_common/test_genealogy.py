# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from utils import testgen
from utils.providers import is_cloud_provider

pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers', 'provider')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.all_providers(metafunc)

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if metafunc.function in {test_vm_genealogy_detected} \
                and args["provider"].type in {"scvmm", "rhevm"}:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="function")
def vm_crud(provider, small_template):
    return VM.factory(
        'test_genealogy_{}'.format(fauxfactory.gen_alpha(length=8).lower()),
        provider, template_name=small_template)


# uncollected above in pytest_generate_tests
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:473"])
@pytest.mark.parametrize("from_edit", [True, False], ids=["via_edit", "via_summary"])
@pytest.mark.uncollectif(
    lambda provider, from_edit: is_cloud_provider(provider.key) and not from_edit)
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
        test_flag: geneaology, provision
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
            parent = pytest.sel.text(opt).strip()
        assert parent.startswith(small_template), "The parent template not detected!"
    else:
        vm_crud_ancestors = vm_crud.genealogy.ancestors
        assert small_template in vm_crud_ancestors, \
            "{} is not in {}'s ancestors".format(small_template, vm_crud.name)
