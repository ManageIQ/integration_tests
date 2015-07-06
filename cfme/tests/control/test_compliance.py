# -*- coding: utf-8 -*-
import re

import diaper
import fauxfactory
import pytest

from cfme.configure.configuration import VMAnalysisProfile
from cfme.control.explorer import (
    VMCompliancePolicy, VMCondition, PolicyProfile)
from cfme.exceptions import VmNotFoundViaIP
from cfme.infrastructure.virtual_machines import Vm
from cfme.web_ui import flash, toolbar
from fixtures.pytest_store import store
from utils import testgen, version
from utils.appliance import Appliance, ApplianceException, provision_appliance
from utils.log import logger
from utils.update import update
from utils.wait import wait_for

PREFIX = "test_compliance_"

pytestmark = [
    # TODO: Problems with fleecing configuration - revisit later
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles=["+automate", "+smartstate", "+smartproxy"]),
    pytest.mark.uncollectif(lambda provider_type: provider_type in {"scvmm"}),
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, "vm_analysis", require_fields=True)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


def wait_for_ssa_enabled():
    wait_for(
        lambda: not toolbar.is_greyed('Configuration', 'Perform SmartState Analysis'),
        delay=10, handle_exception=True, num_sec=600, fail_func=lambda: toolbar.select("Reload"))


@pytest.yield_fixture(scope="module")
def compliance_vm(request, provider_key, provider_crud, provider_type):
    try:
        ip_addr = re.findall(r'[0-9]+(?:\.[0-9]+){3}', store.base_url)[0]
        appl_name = provider_crud.get_mgmt_system().get_vm_name_from_ip(ip_addr)
        appliance = Appliance(provider_key, appl_name)
        logger.info(
            "The tested appliance ({}) is already on this provider ({}) so reusing it.".format(
                appl_name, provider_key))
        try:
            appliance.configure_fleecing()
        except (EOFError, ApplianceException) as e:
            # If something was happening, restart and wait for the UI to reappear to prevent errors
            appliance.ipapp.reboot()
            pytest.skip(
                "Error during appliance configuration. Skipping:\n{}: {}".format(
                    type(e).__name__, str(e)))
        vm = Vm(appl_name, provider_crud)
    except VmNotFoundViaIP:
        logger.info("Provisioning a new appliance on provider {}.".format(provider_key))
        appliance = provision_appliance(
            vm_name_prefix=PREFIX + "host_",
            version=str(version.current_version()),
            provider_name=provider_key)
        request.addfinalizer(lambda: diaper(appliance.destroy))
        try:
            appliance.configure(setup_fleece=True)
        except (EOFError, ApplianceException) as e:   # Add known exceptions as needed.
            pytest.skip(
                "Error during appliance configuration. Skipping:\n{}: {}".format(
                    type(e).__name__, str(e)))
        vm = Vm(appliance.vm_name, provider_crud)
    if provider_type in {"rhevm"}:
        request.addfinalizer(appliance.remove_rhev_direct_lun_disk)
    # Do the final touches
    with appliance.ipapp(browser_steal=True) as appl:
        appl.set_session_timeout(86400)
        provider_crud.refresh_provider_relationships()
        vm.wait_to_appear()
        vm.load_details()
        wait_for_ssa_enabled()
        yield vm


@pytest.yield_fixture(scope="module")
def analysis_profile(compliance_vm):
    ap = VMAnalysisProfile(
        name="default", description="ap-desc", files=[],
        categories=["check_software"])
    if ap.exists:
        ap.delete()
    with ap:
        yield ap


@pytest.fixture(scope="module")
def fleecing_vm(
        request, compliance_vm, vm_analysis, provider_mgmt, provider_key, provider_crud,
        analysis_profile):
    logger.info("Provisioning an appliance for fleecing on {}".format(provider_key))
    # TODO: When we get something smaller, use it!
    appliance = provision_appliance(
        vm_name_prefix=PREFIX + "for_fleece_",
        version=str(version.current_version()),
        provider_name=provider_key)
    request.addfinalizer(lambda: diaper(appliance.destroy))
    logger.info("Appliance {} provisioned".format(appliance.vm_name))
    vm = Vm(appliance.vm_name, provider_crud)
    provider_crud.refresh_provider_relationships()
    vm.wait_to_appear()
    return vm


def do_scan(vm, additional_item_check=None):
    if vm.rediscover_if_analysis_data_present():
        # policy profile assignment is lost so reassign
        vm.assign_policy_profiles(*vm._assigned_pp)

    def _scan():
        return vm.get_detail(properties=("Lifecycle", "Last Analyzed")).lower()
    original = _scan()
    if additional_item_check is not None:
        original_item = vm.get_detail(properties=additional_item_check)
    vm.smartstate_scan(cancel=False, from_details=True)
    flash.assert_message_contain("Smart State Analysis initiated")
    logger.info("Scan initiated")
    wait_for(
        lambda: _scan() != original,
        num_sec=600, delay=5, fail_func=lambda: toolbar.select("Reload"))
    if additional_item_check is not None:
        wait_for(
            lambda: vm.get_detail(properties=additional_item_check) != original_item,
            num_sec=120, delay=5, fail_func=lambda: toolbar.select("Reload"))
    logger.info("Scan finished")


def test_check_package_presence(request, fleecing_vm, ssh_client, vm_analysis, analysis_profile):
    """This test checks compliance by presence of a certain cfme-appliance package which is expected
    to be present on an appliance."""
    # TODO: If we step out from provisioning a full appliance for fleecing, this might need revisit
    condition = VMCondition(
        "Compliance testing condition {}".format(fauxfactory.gen_alphanumeric(8)),
        expression=("fill_find(field=VM and Instance.Guest Applications : Name, "
            "skey=STARTS WITH, value=cfme-appliance, check=Check Count, ckey= = , cvalue=1)")
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = VMCompliancePolicy("Compliance {}".format(fauxfactory.gen_alphanumeric(8)))
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.create()
    policy.assign_conditions(condition)
    profile = PolicyProfile(
        "Compliance PP {}".format(fauxfactory.gen_alphanumeric(8)),
        policies=[policy]
    )
    request.addfinalizer(lambda: diaper(profile.delete))
    profile.create()
    fleecing_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: fleecing_vm.unassign_policy_profiles(profile.description))

    with update(analysis_profile):
        analysis_profile.categories = [
            "check_services", "check_accounts", "check_software", "check_vmconfig", "check_system"]

    do_scan(fleecing_vm)
    assert fleecing_vm.check_compliance_and_wait()


def test_check_files(request, fleecing_vm, ssh_client, analysis_profile):
    """This test checks presence and contents of a certain file. Due to caching, an existing file
    is checked.
    """
    check_file_name = "/etc/sudo.conf"
    check_file_contents = "sudoers_policy"  # The file contains: `Plugin sudoers_policy sudoers.so`
    condition = VMCondition(
        "Compliance testing condition {}".format(fauxfactory.gen_alphanumeric(8)),
        expression=("fill_find(VM and Instance.Files : Name, "
            "=, {}, Check Any, Contents, INCLUDES, {})".format(
                check_file_name, check_file_contents))
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = VMCompliancePolicy("Compliance {}".format(fauxfactory.gen_alphanumeric(8)))
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.create()
    policy.assign_conditions(condition)
    profile = PolicyProfile(
        "Compliance PP {}".format(fauxfactory.gen_alphanumeric(8)),
        policies=[policy]
    )
    request.addfinalizer(lambda: diaper(profile.delete))
    profile.create()
    fleecing_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: fleecing_vm.unassign_policy_profiles(profile.description))

    with update(analysis_profile):
        analysis_profile.files = [(check_file_name, True)]
        analysis_profile.categories = [
            "check_services", "check_accounts", "check_software", "check_vmconfig", "check_system"]

    do_scan(fleecing_vm, ("Configuration", "Files"))
    assert fleecing_vm.check_compliance_and_wait()
