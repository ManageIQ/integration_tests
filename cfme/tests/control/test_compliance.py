# -*- coding: utf-8 -*-
import re

import diaper
import pytest

from cfme.configure import tasks
from cfme.control.explorer import VMCompliancePolicy, VMCondition, PolicyProfile
from cfme.exceptions import VmNotFoundViaIP
from cfme.infrastructure.virtual_machines import Vm
from cfme.web_ui import flash, toolbar
from fixtures.pytest_store import store
from utils import testgen, version
from utils.appliance import Appliance, provision_appliance
from utils.log import logger
from utils.randomness import generate_random_string
from utils.wait import wait_for

PREFIX = "test_compliance_"

pytestmark = [
    # TODO: Problems with fleecing configuration - revisit later
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures("provider_type"),
    pytest.mark.uncollectif(lambda provider_type: provider_type in {"scvmm"}),
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, require_fields=True)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


def wait_for_ssa_enabled():
    wait_for(
        lambda: not toolbar.is_greyed('Configuration', 'Perform SmartState Analysis'),
        delay=10, handle_exception=True, num_sec=600, fail_func=pytest.sel.refresh)


@pytest.yield_fixture(scope="module")
def compliance_vm(request, provider_key, provider_crud):
    try:
        ip_addr = re.findall(r'[0-9]+(?:\.[0-9]+){3}', store.base_url)[0]
        appl_name = provider_crud.get_mgmt_system().get_vm_name_from_ip(ip_addr)
        appliance = Appliance(provider_key, appl_name)
        logger.info(
            "The tested appliance ({}) is already on this provider ({}) so reusing it.".format(
                appl_name, provider_key))
        appliance.configure_fleecing()
        vm = Vm(appl_name, provider_crud)
        with appliance.ipapp:
            provider_crud.refresh_provider_relationships()
            vm.wait_to_appear()
            vm.load_details()
            wait_for_ssa_enabled()
            yield vm
    except VmNotFoundViaIP:
        logger.info("Provisioning a new appliance on provider {}.".format(provider_key))
        appliance = provision_appliance(
            vm_name_prefix=PREFIX,
            version=str(version.current_version()),
            provider_name=provider_key)
        request.addfinalizer(lambda: diaper(appliance.destroy))
        appliance.configure(setup_fleece=True)
        vm = Vm(appliance.vm_name, provider_crud)
        with appliance.ipapp:
            provider_crud.refresh_provider_relationships()
            vm.wait_to_appear()
            vm.load_details()
            wait_for_ssa_enabled()
            yield vm


# TODO: Put it in the Vm class?
def is_vm_analysis_finished(vm_name):
    """ Check if analysis is finished - if not, reload page
    """
    vm_analysis_finished = tasks.tasks_table.find_row_by_cells({
        'task_name': "Scan from Vm %s" % vm_name,
        'state': 'Finished'
    })
    return vm_analysis_finished is not None


def do_scan(vm):
    scan = lambda: vm.get_detail(properties=("Lifecycle", "Last Analyzed")).lower()
    vm.load_details()
    original = scan()
    vm.smartstate_scan(cancel=False, from_details=True)
    flash.assert_message_contain("Smart State Analysis initiated")
    logger.info("Scan initiated")

    # wait for task to complete
    pytest.sel.force_navigate('tasks_my_vm')
    wait_for(is_vm_analysis_finished, [vm.name], delay=15, num_sec=600,
             handle_exception=True, fail_func=lambda: toolbar.select('Reload'))

    # make sure fleecing was successful
    task_row = tasks.tasks_table.find_row_by_cells({
        'task_name': "Scan from Vm {}".format(vm.name),
        'state': 'Finished'
    })
    icon_ele = task_row.row_element.find_elements_by_class_name("icon")
    icon_img = icon_ele[0].find_element_by_tag_name("img")
    assert "checkmark" in icon_img.get_attribute("src")
    vm.load_details()
    wait_for(
        lambda: scan() != original,
        num_sec=300, delay=15, fail_func=lambda: toolbar.select('Reload'))
    logger.info("Scan finished")


def test_check_package_presence(request, compliance_vm, ssh_client):
    """This test checks compliance by presence of a certain software package."""
    condition = VMCondition(
        "Compliance testing condition {}".format(generate_random_string(size=8)),
        expression=("fill_find(VM and Instance.Guest Applications : Name, "
            "=, mc, Check All, Arch ,= ,x86_64)")
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = VMCompliancePolicy("Compliance {}".format(generate_random_string(size=8)))
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.create()
    policy.assign_conditions(condition)
    profile = PolicyProfile(
        "Compliance PP {}".format(generate_random_string(size=8)),
        policies=[policy]
    )
    request.addfinalizer(lambda: diaper(profile.delete))
    profile.create()
    compliance_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: compliance_vm.unassign_policy_profiles(profile.description))
    detail = lambda: compliance_vm.get_detail(properties=("Compliance", "Status")).lower()

    # Non-compliant
    ssh_client.run_command("yum remove -y mc")
    do_scan(compliance_vm)
    compliance_vm.check_compliance()

    wait_for(
        lambda: detail() == "non-compliant as of less than a minute ago",
        num_sec=240,
        delay=1,
        message="VM be non-compliant",
        fail_func=lambda: toolbar.select('Reload')
    )

    # Compliant
    ssh_client.run_command("yum install -y mc")
    do_scan(compliance_vm)
    compliance_vm.check_compliance()

    wait_for(
        lambda: detail() == "compliant as of less than a minute ago",
        num_sec=240,
        delay=1,
        message="VM be non-compliant",
        fail_func=lambda: toolbar.select('Reload')
    )
