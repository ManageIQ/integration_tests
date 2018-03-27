# -*- coding: utf-8 -*-
"""This module tests various ways how to set up the provisioning using the provisioning dialog."""
from datetime import datetime, timedelta

import fauxfactory
import pytest
import re
from widgetastic.utils import partial_match
from widgetastic_patternfly import CheckableBootstrapTreeview as CbTree

from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import Vm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.long_running,
    test_requirements.provision,
    pytest.mark.tier(3),
    pytest.mark.provider([InfraProvider],
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module"),
]


@pytest.fixture(scope="function")
def vm_name():
    vm_name = random_vm_name('provd')
    return vm_name


@pytest.fixture(scope="function")
def prov_data(provisioning, provider):
    data = {
        'request': {
            'email': "{}@{}.test".format(fauxfactory.gen_alphanumeric(),
                                         fauxfactory.gen_alphanumeric()),
            'first_name': fauxfactory.gen_alphanumeric(),
            'last_name': fauxfactory.gen_alphanumeric(),
            'manager_name': '{} {}'.format(fauxfactory.gen_alphanumeric(),
                                           fauxfactory.gen_alphanumeric())},
        'network': {'vlan': partial_match(provisioning.get('vlan'))},
        'environment': {'datastore_name': {'name': provisioning['datastore']},
                        'host_name': {'name': provisioning['host']}},
        'catalog': {},
        'hardware': {},
        'schedule': {},
        'purpose': {},
    }
    if provider.one_of(RHEVMProvider):
        data['catalog']['provision_type'] = 'Native Clone'
    elif provider.one_of(VMwareProvider):
        data['catalog']['provision_type'] = 'VMware'
    # Otherwise just leave it alone
    return data


@pytest.fixture(scope="function")
def provisioner(appliance, request, setup_provider, provider, vm_name):

    def _provisioner(template, provisioning_data, delayed=None):
        vm = Vm(name=vm_name, provider=provider, template_name=template)
        view = navigate_to(vm, 'Provision')
        view.form.fill_with(provisioning_data, on_change=view.form.submit_button)
        base_view = vm.appliance.browser.create_view(BaseLoggedInPage)
        base_view.flash.assert_no_error()

        request.addfinalizer(lambda: VM.factory(vm_name, provider).cleanup_on_provider())
        request_description = 'Provision from [{}] to [{}]'.format(template, vm_name)
        provision_request = appliance.collections.requests.instantiate(
            description=request_description)
        if delayed is not None:
            total_seconds = (delayed - datetime.utcnow()).total_seconds()
            try:
                wait_for(provision_request.is_finished,
                         fail_func=provision_request.update, num_sec=total_seconds, delay=5)
                pytest.fail("The provisioning was not postponed")
            except TimedOutError:
                pass

        logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider.key)
        wait_for(
            provider.mgmt.does_vm_exist, [vm_name],
            fail_func=provider.refresh_provider_relationships,
            handle_exception=True, num_sec=600
        )

        # nav to requests page happens on successful provision
        logger.info('Waiting for cfme provision request for vm %s', vm_name)
        provision_request.wait_for_request()
        msg = "Provisioning failed with the message {}".format(provision_request.rest.message)
        assert provision_request.is_succeeded(), msg
        return vm

    return _provisioner


@pytest.mark.rhv2
def test_change_cpu_ram(provisioner, soft_assert, provider, prov_data, vm_name):
    """ Tests change RAM and CPU in provisioning dialog.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set number of CPUs and amount of RAM.
        * Submit the provisioning request and wait for it to finish.
        * Visit the page of the provisioned VM. The summary should state correct values for CPU&RAM.

    Metadata:
        test_flag: provision
    """
    prov_data['catalog']["vm_name"] = vm_name
    prov_data['hardware']["num_sockets"] = "4"
    prov_data['hardware']["cores_per_socket"] = "1" if not provider.one_of(SCVMMProvider) else None
    prov_data['hardware']["memory"] = "2048"
    template_name = provider.data['provisioning']['template']
    vm = provisioner(template_name, prov_data)

    # Go to the VM info
    view = navigate_to(vm, "Details")
    data = view.entities.summary("Properties").get_text_of("Container").strip()
    # No longer possible to use version pick because of cherrypicking?
    regexes = map(re.compile, [
        r"^[^(]*(\d+) CPUs?.*, ([^)]+)[^)]*$",
        r"^[^(]*\((\d+) CPUs?, ([^)]+)\)[^)]*$",
        r"^.*?(\d+) CPUs? .*?(\d+ MB)$"])
    for regex in regexes:
        match = regex.match(data)
        if match is not None:
            num_cpus, memory = match.groups()
            break
    else:
        raise ValueError("Could not parse string {}".format(repr(data)))
    soft_assert(num_cpus == "4", "num_cpus should be {}, is {}".format("4", num_cpus))
    soft_assert(memory == "2048 MB", "memory should be {}, is {}".format("2048 MB", memory))


@pytest.mark.rhv3
# Special parametrization in testgen above
@pytest.mark.meta(blockers=[1209847, 1380782])
@pytest.mark.parametrize("disk_format", ["Thin", "Thick", "Preallocated"])
@pytest.mark.uncollectif(lambda provider, disk_format:
                         (provider.one_of(RHEVMProvider) and disk_format == "Thick") or
                         (not provider.one_of(RHEVMProvider) and disk_format == "Preallocated") or
                         # Temporarily, our storage domain cannot handle Preallocated disks
                         (provider.one_of(RHEVMProvider) and disk_format == "Preallocated") or
                         (provider.one_of(SCVMMProvider)) or
                         (provider.key == "vsphere55" and disk_format == "Thick"))
def test_disk_format_select(provisioner, disk_format, provider, prov_data, vm_name):
    """ Tests disk format selection in provisioning dialog.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set the disk format to be thick or thin.
        * Submit the provisioning request and wait for it to finish.
        * Visit the page of the provisioned VM.
        * The ``Thin Provisioning Used`` field should state true of false according to the selection

    Metadata:
        test_flag: provision
    """
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['hardware']["disk_format"] = disk_format
    template_name = provider.data['provisioning']['template']

    vm = provisioner(template_name, prov_data)

    # Go to the VM info
    view = navigate_to(vm, 'Details')
    thin = view.entities.summary('Datastore Allocation Summary').get_text_of(
        'Thin Provisioning Used').strip().lower()
    vm.load_details(refresh=True)
    if disk_format == "Thin":
        assert thin == 'true', "The disk format should be Thin"
    else:
        assert thin != 'true', "The disk format should not be Thin"


@pytest.mark.rhv3
@pytest.mark.parametrize("started", [True, False])
def test_power_on_or_off_after_provision(provisioner, prov_data, provider, started, vm_name):
    """ Tests setting the desired power state after provisioning.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set whether you want or not the VM to be
            powered on after provisioning.
        * Submit the provisioning request and wait for it to finish.
        * The VM should become steady in the desired VM power state.

    Metadata:
        test_flag: provision
    """
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['schedule']["power_on"] = started
    template_name = provider.data['provisioning']['template']

    provisioner(template_name, prov_data)

    wait_for(
        lambda: provider.mgmt.does_vm_exist(vm_name) and
        (provider.mgmt.is_vm_running if started else provider.mgmt.is_vm_stopped)(vm_name),
        num_sec=240, delay=5
    )


@pytest.mark.rhv3
def test_tag(provisioner, prov_data, provider, vm_name):
    """ Tests tagging VMs using provisioning dialogs.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, pick a tag.
        * Submit the provisioning request and wait for it to finish.
        * Visit th page of VM, it should display the selected tags


    Metadata:
        test_flag: provision
    """
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['purpose']["apply_tags"] = CbTree.CheckNode(path=("Service Level *", "Gold"))
    template_name = provider.data['provisioning']['template']

    vm = provisioner(template_name, prov_data)

    tags = vm.get_tags()
    assert any(
        tag.category.display_name == "Service Level" and tag.display_name == "Gold"
        for tag in tags
    ), "Service Level: Gold not in tags ({})".format(tags)


@pytest.mark.rhv3
@pytest.mark.meta(blockers=[1204115])
def test_provisioning_schedule(provisioner, provider, prov_data, vm_name):
    """ Tests provision scheduling.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set a scheduled provision and pick a time.
        * Submit the provisioning request, it should not start before the scheduled time.

    Metadata:
        test_flag: provision
    """
    now = datetime.utcnow()
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['schedule']["schedule_type"] = "Schedule"
    prov_data['schedule']["provision_date"] = now.strftime("%m/%d/%Y")
    STEP = 5
    minutes_diff = (STEP - (now.minute % STEP))
    # To have some gap for automation
    if minutes_diff <= 3:
        minutes_diff += 5
    provision_time = timedelta(minutes=minutes_diff) + now
    prov_data['schedule']["provision_start_hour"] = str(provision_time.hour)
    prov_data['schedule']["provision_start_min"] = str(provision_time.minute)

    template_name = provider.data['provisioning']['template']

    provisioner(template_name, prov_data, delayed=provision_time)
