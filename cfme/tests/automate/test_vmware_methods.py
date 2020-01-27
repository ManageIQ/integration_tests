"""This module contains tests that exercise the canned VMware Automate stuff."""
from textwrap import dedent

import fauxfactory
import pytest
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.common import BaseLoggedInPage
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.generators import random_vm_name
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
def cls(domain):
    original_class = domain.parent\
        .instantiate(name='ManageIQ')\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')
    original_class.copy_to(domain=domain)
    return domain.namespaces.instantiate(name='System').classes.instantiate(name='Request')


@pytest.fixture(scope="module")
def testing_group(appliance):
    group_desc = fauxfactory.gen_alphanumeric()
    group = appliance.collections.button_groups.create(
        text=group_desc,
        hover=group_desc,
        type=appliance.collections.button_groups.VM_INSTANCE
    )
    yield group
    group.delete_if_exists()


@pytest.fixture(scope="function")
def testing_vm(setup_provider, provider):
    collection = provider.appliance.provider_based_collection(provider)
    try:
        template_name = provider.data['templates']['full_template']['name']
    except KeyError:
        pytest.skip('Unable to identify full_template for provider: {}'.format(provider))

    vm = collection.instantiate(
        random_vm_name("ae-hd"),
        provider,
        template_name=template_name
    )
    try:
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        yield vm
    finally:
        vm.cleanup_on_provider()


def test_vmware_vimapi_hotadd_disk(
        appliance, request, testing_group, testing_vm, domain, cls):
    """Tests hot adding a disk to vmware vm. This test exercises the `VMware_HotAdd_Disk` method,
       located in `/Integration/VMware/VimApi`

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        casecomponent: Automate
        caseimportance: critical
        tags: automate
        testSteps:
            1. It creates an instance in ``System/Request`` that can be accessible from eg. button
            2. Then it creates a button, that refers to the ``VMware_HotAdd_Disk`` in ``Request``.
               The button shall belong in the VM and instance button group.
            3. After the button is created, it goes to a VM's summary page, clicks the button.
            4. The test waits until the capacity of disks is raised.

    Bugzilla:
        1211627
        1311221
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
    button = testing_group.buttons.create(
        text=button_name,
        hover=button_name,
        system="Request",
        request=instance.name)
    request.addfinalizer(button.delete_if_exists)

    def _get_disk_capacity():
        view = testing_vm.load_details(refresh=True)
        return view.entities.summary('Datastore Allocation Summary').get_text_of('Total Allocation')

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
