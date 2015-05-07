# -*- coding: utf-8 -*-
import pytest
import re
from datetime import datetime, timedelta

from cfme.infrastructure.virtual_machines import Vm, details_page
from cfme.provisioning import provisioning_form
from cfme.services import requests
from cfme.web_ui import fill, flash
from utils import testgen, version
from utils.log import logger
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.wait import wait_for, TimedOutError


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.sel.go_to("dashboard"),
    pytest.mark.long_running
]


def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        if provider_mgmt.does_vm_exist(vm_name):
            logger.info('Cleaning up VM {} on provider {}'.format(vm_name, provider_key))
            provider_mgmt.delete_vm(vm_name)
    except Exception as e:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM {} on provider {} ({})'.format(
            vm_name, provider_key, str(e)))


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
def prov_data(provisioning, provider_type):
    if provider_type == "scvmm":
        pytest.skip("SCVMM does not support provisioning yet!")  # TODO: After fixing - remove

    return {
        "first_name": generate_random_string(),
        "last_name": generate_random_string(),
        "email": "{}@{}.test".format(generate_random_string(), generate_random_string()),
        "manager_name": "{} {}".format(generate_random_string(), generate_random_string()),
        "vlan": provisioning.get("vlan", None),
        # "datastore_create": False,
        "datastore_name": {"name": provisioning["datastore"]},
        "host_name": {"name": provisioning["host"]},
        # "catalog_name": provisioning["catalog_item_type"],
        "provision_type": "Native Clone" if provider_type == "rhevm" else "VMware"
    }


@pytest.fixture(scope="function")
def template_name(provisioning):
    return provisioning["template"]


@pytest.fixture(scope="function")
def provisioner(request, provider_key, provider_mgmt, provider_crud):
    if not provider_crud.exists:
        setup_provider(provider_key)

    def _provisioner(template, provisioning_data, delayed=None):
        pytest.sel.force_navigate('infrastructure_provision_vms', context={
            'provider': provider_crud,
            'template_name': template,
        })

        vm_name = provisioning_data["vm_name"]
        fill(provisioning_form, provisioning_data, action=provisioning_form.submit_button)
        flash.assert_no_errors()

        request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))
        if delayed is not None:
            total_seconds = (delayed - datetime.utcnow()).total_seconds()
            row_description = 'Provision from [%s] to [%s]' % (template, vm_name)
            cells = {'Description': row_description}
            try:
                row, __ = wait_for(requests.wait_for_request, [cells],
                                   fail_func=requests.reload, num_sec=total_seconds, delay=5)
                pytest.fail("The provisioning was not postponed")
            except TimedOutError:
                pass
        logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider_crud.key)
        wait_for(provider_mgmt.does_vm_exist, [vm_name], handle_exception=True, num_sec=600)

        # nav to requests page happens on successful provision
        logger.info('Waiting for cfme provision request for vm %s' % vm_name)
        row_description = 'Provision from [%s] to [%s]' % (template, vm_name)
        cells = {'Description': row_description}
        row, __ = wait_for(requests.wait_for_request, [cells],
                           fail_func=requests.reload, num_sec=900, delay=20)
        assert row.last_message.text == version.pick(
            {version.LOWEST: 'VM Provisioned Successfully',
             "5.3": 'Vm Provisioned Successfully', })
        return Vm(vm_name, provider_crud)

    return _provisioner


def test_change_cpu_ram(provisioner, prov_data, template_name, soft_assert):
    """ Tests change RAM and CPU

    Metadata:
        test_flag: provision
    """
    prov_data["vm_name"] = "test_prov_dlg_{}".format(generate_random_string())
    prov_data["num_sockets"] = "4"
    prov_data["cores_per_socket"] = "1"
    prov_data["memory"] = "4096"

    vm = provisioner(template_name, prov_data)

    # Go to the VM info
    data = vm.get_detail(properties=("Properties", "Container")).strip()
    regex = version.pick({version.LOWEST: r"^[^(]*\((\d+) CPUs?, ([^)]+)\)[^)]*$",
                          '5.4': r"^.*?(\d+) CPUs? .*?(\d+ MB)$"})
    num_cpus, memory = re.match(regex, data).groups()
    soft_assert(num_cpus == "4", "num_cpus should be {}, is {}".format("4", num_cpus))
    soft_assert(memory == "4096 MB", "memory should be {}, is {}".format("4096 MB", memory))


# Special parametrization in testgen above
@pytest.mark.meta(blockers=[1209847])
@pytest.mark.parametrize("disk_format", ["thin", "thick", "preallocated"])
@pytest.mark.uncollectif(lambda provider_type, disk_format:
                         (provider_type == "rhevm" and disk_format == "thick") or
                         (provider_type != "rhevm" and disk_format == "preallocated"))
def test_disk_format_select(provisioner, prov_data, template_name, disk_format, provider_type):
    """ Tests disk format

    Metadata:
        test_flag: provision
    """
    prov_data["vm_name"] = "test_prov_dlg_{}".format(generate_random_string())
    prov_data["disk_format"] = disk_format

    vm = provisioner(template_name, prov_data)

    # Go to the VM info
    vm.load_details(refresh=True)
    thin = details_page.infoblock.text(
        "Datastore Allocation Summary", "Thin Provisioning Used").strip().lower() == "true"
    if disk_format == "thin":
        assert thin, "The disk format should be Thin"
    else:
        assert not thin, "The disk format should not be Thin"


@pytest.mark.parametrize("started", [True, False])
def test_power_on_or_off_after_provision(
        provisioner, prov_data, template_name, provider_mgmt, started):
    """ Tests power cycle after provisioning

    Metadata:
        test_flag: provision
    """
    prov_data["vm_name"] = "test_prov_dlg_{}".format(generate_random_string())
    prov_data["power_on"] = started

    provisioner(template_name, prov_data)

    wait_for(
        lambda: provider_mgmt.does_vm_exist(prov_data["vm_name"]) and
        provider_mgmt.is_vm_running(prov_data["vm_name"]) == started,
        num_sec=240, delay=5
    )


@pytest.mark.uncollectif(lambda: version.current_version() < '5.3')
def test_tag(provisioner, prov_data, template_name, provider_type):
    """ Tests tagging

    Metadata:
        test_flag: provision
    """
    prov_data["vm_name"] = "test_prov_dlg_{}".format(generate_random_string())
    prov_data["apply_tags"] = [
        ([version.pick({version.LOWEST: "Service Level", "5.3": "Service Level *"}), "Gold"], True)]

    vm = provisioner(template_name, prov_data)

    tags = vm.get_tags()
    assert "Service Level: Gold" in tags, "Service Level: Gold not in tags ({})".format(str(tags))


@pytest.mark.meta(blockers=[1204115])
def test_provisioning_schedule(provisioner, prov_data, template_name):
    """ Tests provision scheduling

    Metadata:
        test_flag: provision
    """
    prov_data["vm_name"] = "test_prov_dlg_{}".format(generate_random_string())
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
