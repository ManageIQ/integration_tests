# -*- coding: utf-8 -*-
"""This module contains tests that exercise the canned VMware Automate stuff."""
import fauxfactory
import pytest

from textwrap import dedent

from cfme.automate.buttons import ButtonGroup, Button
from cfme.automate.explorer import Namespace, Class, Instance, Domain, Method
from cfme.automate.service_dialogs import ServiceDialog
from cfme.common.vm import VM
from cfme.web_ui import fill, flash, form_buttons, toolbar, Input
from utils import testgen
from utils.blockers import BZ
from utils.log import logger
from utils.wait import wait_for

submit = form_buttons.FormButton("Submit")
pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("upstream")]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'], 'provisioning')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


@pytest.yield_fixture(scope="module")
def domain(request):
    domain = Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    yield domain
    if domain.exists():
        domain.delete()


@pytest.fixture(scope="module")
def cls(request, domain):
    original_class = Class(
        name='Request', namespace=Namespace(name='System', domain=Domain(name='ManageIQ (Locked)')))
    return original_class.copy_to(domain)
    # No finalizer because whole domain will get nuked


@pytest.yield_fixture(scope="module")
def testing_group(request):
    group_desc = fauxfactory.gen_alphanumeric()
    group = ButtonGroup(
        text=group_desc,
        hover=group_desc,
        type=ButtonGroup.VM_INSTANCE
    )
    group.create()
    yield group
    group.delete_if_exists()


@pytest.yield_fixture(scope="function")
def testing_vm(request, provisioning, setup_provider, provider):
    vm = VM.factory(
        "test_ae_hd_{}".format(fauxfactory.gen_alphanumeric()),
        provider,
        template_name=provisioning["template"]
    )
    try:
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        yield vm
    finally:
        vm.delete_from_provider()
        if vm.exists:
            vm.delete()


@pytest.mark.meta(blockers=[1211627, BZ(1311221, forced_streams=['5.5'])])
def test_vmware_vimapi_hotadd_disk(
        request, testing_group, provider, testing_vm, domain, cls):
    """ Tests hot adding a disk to vmware vm.

    This test exercises the ``VMware_HotAdd_Disk`` method, located in ``/Integration/VMware/VimApi``

    Steps:
        * It creates an instance in ``System/Request`` that can be accessible from eg. a button.
        * Then it creates a service dialog that contains a field with the desired disk size, the
            text field name should be ``size``
        * Then it creates a button, that refers to the ``VMware_HotAdd_Disk`` in ``Request``. The
            button shall belong in the VM and instance button group.
        * After the button is created, it goes to a VM's summary page, clicks the button, enters
            the size of the disk and submits the dialog.
        * The test waits until the number of disks is raised.

    Metadata:
        test_flag: hotdisk, provision
    """
    meth = Method(
        name='parse_dialog_value_{}'.format(fauxfactory.gen_alpha()),
        data=dedent('''\
            # Transfers the dialog value to the root so the VMware method can use it.

            $evm.root['size'] = $evm.object['dialog_size']
            exit MIQ_OK
            '''),
        cls=cls)

    @request.addfinalizer
    def _remove_method():
        if meth.exists():
            meth.delete()

    meth.create()

    # Instance that calls the method and is accessible from the button
    instance = Instance(
        name="VMware_HotAdd_Disk_{}".format(fauxfactory.gen_alpha()),
        values={
            "meth4": {'on_entry': meth.name},  # To preparse the value
            "rel5": "/Integration/VMware/VimApi/VMware_HotAdd_Disk",
        },
        cls=cls
    )

    @request.addfinalizer
    def _remove_instance():
        if instance.exists():
            instance.delete()
    instance.create()
    # Dialog to put the disk capacity
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
    request.addfinalizer(dialog.delete)
    # Button that will invoke the dialog and action
    button_name = fauxfactory.gen_alphanumeric()
    button = Button(group=testing_group,
                    text=button_name,
                    hover=button_name,
                    dialog=dialog, system="Request", request=instance.name)
    request.addfinalizer(button.delete_if_exists)
    button.create()

    def _get_disk_count():
        return int(testing_vm.get_detail(
            properties=("Datastore Allocation Summary", "Number of Disks")).strip())
    original_disk_count = _get_disk_count()
    logger.info('Initial disk count: %s', original_disk_count)
    toolbar.select(testing_group.text, button.text)
    fill(Input("size"), '1')
    pytest.sel.click(submit)
    flash.assert_no_errors()
    try:
        wait_for(
            lambda: original_disk_count + 1 == _get_disk_count(), num_sec=180, delay=5)
    finally:
        logger.info('End disk count: %s', _get_disk_count())
