# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.buttons import ButtonGroup, Button
from cfme.automate.explorer import Namespace, Class, Instance, Domain
from cfme.automate.service_dialogs import ServiceDialog
from cfme.infrastructure.virtual_machines import Vm
from cfme.web_ui import fill, flash, form_buttons, toolbar, Input
from utils import testgen
from utils.providers import setup_provider
from utils.version import current_version  # NOQA
from utils.wait import wait_for

submit = form_buttons.FormButton("Submit")
pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("upstream", "5.3"), ]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'], 'provisioning')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


@pytest.fixture(scope="module")
def domain(request):
    if current_version < "5.3":
        return None
    domain = Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="module")
def namespace(request, domain):
    namespace = Namespace(name="System", description="System", parent=domain)
    namespace.create()
    request.addfinalizer(lambda: namespace.delete() if namespace.exists() else None)
    return namespace


@pytest.fixture(scope="module")
def cls(request, domain, namespace):
    tcls = Class(name="Request", namespace=namespace,
                 setup_schema=[Class.SchemaField(name="rel5", type_="Relationship")])
    tcls.create()
    request.addfinalizer(lambda: tcls.delete() if tcls.exists() else None)
    return tcls


@pytest.fixture(scope="module")
def testing_group(request):
    group_desc = fauxfactory.gen_alphanumeric()
    group = ButtonGroup(
        text=group_desc,
        hover=group_desc,
        type=ButtonGroup.VM_INSTANCE
    )
    request.addfinalizer(group.delete_if_exists)
    group.create()
    return group


@pytest.fixture(scope="function")
def testing_vm(request, provisioning, provider_crud, provider_key):
    setup_provider(provider_key)
    vm = Vm(
        name="test_ae_hd_{}".format(fauxfactory.gen_alphanumeric()),
        provider_crud=provider_crud,
        template_name=provisioning["template"]
    )

    def _finalize():
        vm.delete_from_provider()
        if vm.does_vm_exist_in_cfme():
            vm.remove_from_cfme()
    request.addfinalizer(_finalize)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm


@pytest.mark.meta(blockers=[1211627])
def test_vmware_vimapi_hotadd_disk(
        request, testing_group, provider_crud, provider_mgmt, testing_vm, domain, namespace, cls):
    """ Tests hot adding a disk to vmware vm

    Metadata:
        test_flag: hotdisk, provision
    """
    # Instance that calls the method and is accessible from the button
    if current_version() < "5.3":
        rel = "/Integration/VimApi/VMware_HotAdd_Disk"
    else:
        rel = "/Integration/VMware/VimApi/VMware_HotAdd_Disk"
    instance = Instance(
        name="VMware_HotAdd_Disk",
        values={
            "rel5": rel,
        },
        cls=cls
    )
    if not instance.exists():
        request.addfinalizer(lambda: instance.delete() if instance.exists() else None)
        instance.create()
    # Dialog to put the disk capacity
    return
    element_data = {
        'ele_label': "Disk size",
        'ele_name': "size",
        'ele_desc': "Disk size",
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(
        label=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        submit=True,
        tab_label=fauxfactory.gen_alphanumeric(),
        tab_desc=fauxfactory.gen_alphanumeric(),
        box_label=fauxfactory.gen_alphanumeric(),
        box_desc=fauxfactory.gen_alphanumeric(),
    )
    dialog.create(element_data)
    request.addfinalizer(lambda: dialog.delete())
    # Button that will invoke the dialog and action
    button_name = fauxfactory.gen_alphanumeric()
    button = Button(group=testing_group,
                    text=button_name,
                    hover=button_name,
                    dialog=dialog, system="Request", request="VMware_HotAdd_Disk")
    request.addfinalizer(button.delete_if_exists)
    button.create()
    # Now do the funny stuff

    def _get_disk_count():
        return int(testing_vm.get_detail(
            properties=("Datastore Allocation Summary", "Number of Disks")).strip())
    original_disk_count = _get_disk_count()
    toolbar.select(testing_group.text, button.text)
    fill(Input("size"), "1")
    pytest.sel.click(submit)
    flash.assert_no_errors()
    wait_for(lambda: original_disk_count + 1 == _get_disk_count(), num_sec=180, delay=5)
