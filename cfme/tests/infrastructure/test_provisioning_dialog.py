# -*- coding: utf-8 -*-
"""This module tests various ways how to set up the provisioning using the provisioning dialog."""
import fauxfactory
import pytest
import re
from datetime import datetime, timedelta

from cfme.common.provider import cleanup_vm
from cfme.common.vm import VM
from cfme.provisioning import provisioning_form
from cfme.services import requests
from cfme.web_ui import InfoBlock, fill, flash
from utils import mgmt_system, testgen
from utils.blockers import BZ
from utils.log import logger
from utils.wait import wait_for, TimedOutError


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.sel.go_to("dashboard"),
    pytest.mark.long_running,
    pytest.mark.meta(blockers=[
        BZ(
            1265466,
            unblock=lambda provider: not isinstance(provider.mgmt, mgmt_system.RHEVMSystem))
    ])
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, 'provisioning', template_location=["provisioning", "template"])

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        # required keys should be a subset of the dict keys set
        if not {'template', 'host', 'datastore'}.issubset(args['provisioning'].viewkeys()):
            # Need all three for template provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="function")
def prov_data(provisioning, provider):
    data = {
        "first_name": fauxfactory.gen_alphanumeric(),
        "last_name": fauxfactory.gen_alphanumeric(),
        "email": "{}@{}.test".format(
            fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric()),
        "manager_name": "{} {}".format(
            fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric()),
        "vlan": provisioning.get("vlan", None),
        # "datastore_create": False,
        "datastore_name": {"name": provisioning["datastore"]},
        "host_name": {"name": provisioning["host"]},
        # "catalog_name": provisioning["catalog_item_type"],
    }

    if provider.type == 'rhevm':
        data['provision_type'] = 'Native Clone'
    elif provider.type == 'virtualcenter':
        data['provision_type'] = 'VMware'
    # Otherwise just leave it alone

    return data


@pytest.fixture(scope="function")
def template_name(provisioning):
    return provisioning["template"]


@pytest.fixture(scope="function")
def provisioner(request, setup_provider, provider):

    def _provisioner(template, provisioning_data, delayed=None):
        pytest.sel.force_navigate('infrastructure_provision_vms', context={
            'provider': provider,
            'template_name': template,
        })

        vm_name = provisioning_data["vm_name"]
        fill(provisioning_form, provisioning_data, action=provisioning_form.submit_button)
        flash.assert_no_errors()

        request.addfinalizer(lambda: cleanup_vm(vm_name, provider))
        if delayed is not None:
            total_seconds = (delayed - datetime.utcnow()).total_seconds()
            row_description = 'Provision from [{}] to [{}]'.format(template, vm_name)
            cells = {'Description': row_description}
            try:
                row, __ = wait_for(requests.wait_for_request, [cells],
                                   fail_func=requests.reload, num_sec=total_seconds, delay=5)
                pytest.fail("The provisioning was not postponed")
            except TimedOutError:
                pass
        logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider.key)
        wait_for(provider.mgmt.does_vm_exist, [vm_name], handle_exception=True, num_sec=600)

        # nav to requests page happens on successful provision
        logger.info('Waiting for cfme provision request for vm %s', vm_name)
        row_description = 'Provision from [{}] to [{}]'.format(template, vm_name)
        cells = {'Description': row_description}
        row, __ = wait_for(requests.wait_for_request, [cells],
                           fail_func=requests.reload, num_sec=900, delay=20)
        assert row.last_message.text == 'Vm Provisioned Successfully'
        return VM.factory(vm_name, provider)

    return _provisioner


def test_change_cpu_ram(provisioner, prov_data, template_name, soft_assert):
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
    prov_data["vm_name"] = "test_prov_dlg_{}".format(fauxfactory.gen_alphanumeric())
    prov_data["num_sockets"] = "4"
    prov_data["cores_per_socket"] = "1"
    prov_data["memory"] = "4096"

    vm = provisioner(template_name, prov_data)

    # Go to the VM info
    data = vm.get_detail(properties=("Properties", "Container")).strip()
    # No longer possible to use version pick because of cherrypicking?
    regexes = map(re.compile, [
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
    soft_assert(memory == "4096 MB", "memory should be {}, is {}".format("4096 MB", memory))


# Special parametrization in testgen above
@pytest.mark.meta(blockers=[1209847])
@pytest.mark.parametrize("disk_format", ["thin", "thick", "preallocated"])
@pytest.mark.uncollectif(lambda provider, disk_format:
                         (provider.type == "rhevm" and disk_format == "thick") or
                         (provider.type != "rhevm" and disk_format == "preallocated") or
                         # Temporarily, our storage domain cannot handle preallocated disks
                         (provider.type == "rhevm" and disk_format == "preallocated"))
def test_disk_format_select(provisioner, prov_data, template_name, disk_format, provider):
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
    prov_data["vm_name"] = "test_prov_dlg_{}".format(fauxfactory.gen_alphanumeric())
    prov_data["disk_format"] = disk_format

    vm = provisioner(template_name, prov_data)

    # Go to the VM info
    vm.load_details(refresh=True)
    thin = InfoBlock.text(
        "Datastore Allocation Summary", "Thin Provisioning Used").strip().lower() == "true"
    if disk_format == "thin":
        assert thin, "The disk format should be Thin"
    else:
        assert not thin, "The disk format should not be Thin"


@pytest.mark.parametrize("started", [True, False])
def test_power_on_or_off_after_provision(provisioner, prov_data, template_name, provider, started):
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
    vm_name = "test_prov_dlg_{}".format(fauxfactory.gen_alphanumeric())
    prov_data["vm_name"] = vm_name
    prov_data["power_on"] = started

    provisioner(template_name, prov_data)

    wait_for(
        lambda: provider.mgmt.does_vm_exist(vm_name) and
        (provider.mgmt.is_vm_running if started else provider.mgmt.is_vm_stopped)(vm_name),
        num_sec=240, delay=5
    )


def test_tag(provisioner, prov_data, template_name, provider):
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
    prov_data["vm_name"] = "test_prov_dlg_{}".format(fauxfactory.gen_alphanumeric())
    prov_data["apply_tags"] = [(["Service Level *", "Gold"], True)]

    vm = provisioner(template_name, prov_data)

    tags = vm.get_tags()
    assert "Service Level: Gold" in tags, "Service Level: Gold not in tags ({})".format(str(tags))


@pytest.mark.meta(blockers=[1204115])
def test_provisioning_schedule(provisioner, prov_data, template_name):
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
    prov_data["vm_name"] = "test_prov_dlg_{}".format(fauxfactory.gen_alphanumeric())
    prov_data["schedule_type"] = "schedule"
    now = datetime.utcnow()
    prov_data["provision_date"] = now.strftime("%m/%d/%Y")
    STEP = 5
    minutes_diff = (STEP - (now.minute % STEP))
    # To have some gap for automation
    if minutes_diff <= 3:
        minutes_diff += 5
    provision_time = timedelta(minutes=minutes_diff) + now
    prov_data["provision_start_hour"] = str(provision_time.hour)
    prov_data["provision_start_min"] = str(provision_time.minute)

    provisioner(template_name, prov_data, delayed=provision_time)
