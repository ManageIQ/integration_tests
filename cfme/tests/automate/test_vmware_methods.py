# -*- coding: utf-8 -*-
import pytest

from cfme.automate.buttons import ButtonGroup, Button
from cfme.automate.explorer import Namespace, Class, Instance
from cfme.automate.service_dialogs import ServiceDialog
from cfme.infrastructure.virtual_machines import Vm
from cfme.web_ui import fill, flash, form_buttons, toolbar
from utils import testgen
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.version import current_version  # NOQA
from utils.wait import wait_for

submit = form_buttons.FormButton("Submit")
pytestmark = [
    pytest.mark.usefixtures("server_roles"),
    pytest.mark.fixtureconf(server_roles="+automate"),
    pytest.mark.ignore_stream("upstream", "5.3"), ]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'], 'provisioning')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


@pytest.fixture(scope="module")
def testing_group(request):
    group_desc = generate_random_string()
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
        name=generate_random_string(),
        provider_crud=provider_crud,
        template_name=provisioning["template"]
    )
    request.addfinalizer(lambda: vm.remove_from_cfme())
    request.addfinalizer(lambda: vm.delete_from_provider())
    vm.create_on_provider()
    return vm


def test_vmware_vimapi_hotadd_disk(
        request, testing_group, provider_crud, provider_mgmt, testing_vm):
    # Instance that calls the method and is accessible from the button
    instance = Instance(
        name="VMware_HotAdd_Disk",
        values={
            "rel5": "/Integration/VimApi/VMware_HotAdd_Disk",
        },
        cls=Class(
            name="Automation Requests (Request)",
            namespace=Namespace(
                name="System"
            ),
        )
    )
    if not instance.exists():
        request.addfinalizer(lambda: instance.delete() if instance.exists() else None)
        instance.create()
    # Dialog to put the disk capacity
    dialog = ServiceDialog(
        label=generate_random_string(),
        description=generate_random_string(),
        submit=True,
        tab_label=generate_random_string(),
        tab_desc=generate_random_string(),
        box_label=generate_random_string(),
        box_desc=generate_random_string(),
        ele_label="Disk size",
        ele_name="size",
        ele_desc="Disk size",
        choose_type="Text Box",
    )
    dialog.create()
    request.addfinalizer(lambda: dialog.delete())
    # Button that will invoke the dialog and action
    button_name = generate_random_string()
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
    fill("input#size", "1")
    pytest.sel.click(submit)
    flash.assert_no_errors()
    wait_for(lambda: original_disk_count + 1 == _get_disk_count(), num_sec=180, delay=5)
