# -*- coding: utf-8 -*-
"""This module contains tests that exercise the canned VMware Automate stuff."""
from textwrap import dedent

import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown
from widgetastic.widget import View

from cfme import test_requirements
from cfme.automate.buttons import ButtonGroup, Button
from cfme.automate.explorer.domain import DomainCollection
from cfme.base.login import BaseLoggedInPage
from cfme.common.vm import VM
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.automate,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.tier(3),
    pytest.mark.provider(
        [VMwareProvider], required_fields=[['provisioning', 'template']],
        scope="module")
]


@pytest.fixture(scope="module")
def domain_collection(appliance):
    return DomainCollection(appliance)


@pytest.yield_fixture(scope="module")
def domain(request, domain_collection):
    domain = domain_collection.create(name=fauxfactory.gen_alphanumeric(), enabled=True)
    yield domain
    if domain.exists:
        domain.delete()


@pytest.fixture(scope="module")
def cls(request, domain):
    original_class = domain.parent\
        .instantiate(name='ManageIQ')\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')
    original_class.copy_to(domain=domain)
    return domain.namespaces.instantiate(name='System').classes.instantiate(name='Request')


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
def testing_vm(request, setup_provider, provider):
    vm = VM.factory(
        "test_ae_hd_{}".format(fauxfactory.gen_alphanumeric()),
        provider,
        template_name=provider.data['full_template']['name']
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
        appliance, request, testing_group, provider, testing_vm, domain, cls):
    """ Tests hot adding a disk to vmware vm.

    This test exercises the ``VMware_HotAdd_Disk`` method, located in ``/Integration/VMware/VimApi``

    Steps:
        * It creates an instance in ``System/Request`` that can be accessible from eg. a button.
        * Then it creates a button, that refers to the ``VMware_HotAdd_Disk`` in ``Request``. The
            button shall belong in the VM and instance button group.
        * After the button is created, it goes to a VM's summary page, clicks the button.
        * The test waits until the capacity of disks is raised.

    Metadata:
        test_flag: hotdisk, provision
    """
    meth = cls.methods.create(
        name='load_value_{}'.format(fauxfactory.gen_alpha()),
        script=dedent('''\
            # Sets the capacity of the new disk.

            $evm.root['size'] = 1  # GB
            exit MIQ_OK
            '''))

    request.addfinalizer(meth.delete_if_exists)

    # Instance that calls the method and is accessible from the button
    instance = cls.instances.create(
        name="VMware_HotAdd_Disk_{}".format(fauxfactory.gen_alpha()),
        fields={
            "meth4": {'value': meth.name},  # To get the value
            "rel5": {'value': "/Integration/VMware/VimApi/VMware_HotAdd_Disk"},
        },
    )

    request.addfinalizer(instance.delete_if_exists)

    # Button that will invoke the dialog and action
    button_name = fauxfactory.gen_alphanumeric()
    button = Button(group=testing_group,
                    text=button_name,
                    hover=button_name, system="Request", request=instance.name)
    request.addfinalizer(button.delete_if_exists)
    button.create()

    def _get_disk_capacity():
        testing_vm.summary.reload()
        return testing_vm.summary.datastore_allocation_summary.total_allocation.value

    original_disk_capacity = _get_disk_capacity()
    logger.info('Initial disk allocation: %s', original_disk_capacity)

    class CustomButtonView(View):
        custom_button = Dropdown(testing_group.text)

    view = appliance.browser.create_view(CustomButtonView)
    view.custom_button.item_select(button.text)

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_no_error()
    try:
        wait_for(
            lambda: _get_disk_capacity() > original_disk_capacity, num_sec=180, delay=5)
    finally:
        logger.info('End disk capacity: %s', _get_disk_capacity())
