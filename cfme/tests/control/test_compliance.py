# -*- coding: utf-8 -*-
import diaper
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.control.explorer.policies import VMCompliancePolicy, HostCompliancePolicy
from cfme.control.explorer.conditions import VMCondition
from cfme.control.explorer.policy_profiles import PolicyProfile
from cfme.infrastructure.provider import InfraProvider
from cfme.configure.configuration import AnalysisProfile
from cfme.web_ui import flash, toolbar
from utils import testgen, version
from utils.log import logger
from utils.providers import setup_a_provider_by_class
from utils.update import update
from utils.wait import wait_for
from cfme import test_requirements

PREFIX = "test_compliance_"


@pytest.fixture(scope="module")
def setup_a_provider():
    setup_a_provider_by_class(InfraProvider)

pytestmark = [
    # TODO: Problems with fleecing configuration - revisit later
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles=["+automate", "+smartstate", "+smartproxy"]),
    pytest.mark.uncollectif(lambda provider: provider.type in {"scvmm"}),
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_a_provider"),
    test_requirements.control
]


pytest_generate_tests = testgen.generate(
    [InfraProvider], required_fields=["vm_analysis"], scope="module")


def wait_for_ssa_enabled():
    wait_for(
        lambda: not toolbar.is_greyed('Configuration', 'Perform SmartState Analysis'),
        delay=10, handle_exception=True, num_sec=600, fail_func=lambda: toolbar.select("Reload"))


@pytest.fixture
def policy_name():
    return "compliance_testing: policy {}".format(fauxfactory.gen_alphanumeric(8))


@pytest.fixture
def policy_profile_name():
    return "compliance_testing: policy profile {}".format(fauxfactory.gen_alphanumeric(8))


@pytest.fixture
def host(provider, setup_provider):
    return provider.hosts[0]


@pytest.yield_fixture
def policy_for_testing(policy_name, policy_profile_name, provider):
    policy = HostCompliancePolicy(policy_name)
    policy.create()
    policy_profile = PolicyProfile(policy_profile_name, policies=[policy])
    policy_profile.create()
    yield policy
    policy_profile.delete()
    policy.delete()


@pytest.yield_fixture
def assign_policy_for_testing(policy_for_testing, host, policy_profile_name):
    host.assign_policy_profiles(policy_profile_name)
    yield policy_for_testing
    host.unassign_policy_profiles(policy_profile_name)


@pytest.yield_fixture(scope="module")
def compliance_vm(request, provider, temp_appliance_for_cur_provider):
    appliance = temp_appliance_for_cur_provider
    appliance.configure_fleecing()
    vm = VM.factory(appliance.vm_name, provider)

    if provider.type in {"rhevm"}:
        request.addfinalizer(appliance.remove_rhev_direct_lun_disk)
    # Do the final touches
    with appliance.ipapp(browser_steal=True) as appl:
        appl.set_session_timeout(86400)
        provider.refresh_provider_relationships()
        vm.wait_to_appear()
        vm.load_details()
        wait_for_ssa_enabled()
        yield vm


@pytest.yield_fixture(scope="module")
def analysis_profile(compliance_vm):
    ap = AnalysisProfile(name="default", description="ap-desc", profile_type='VM', files=[],
                         categories=["check_software"])
    if ap.exists:
        ap.delete()
    with ap:
        yield ap


@pytest.fixture(scope="module")
def fleecing_vm(request, compliance_vm, provider, analysis_profile,
                temp_appliance_for_cur_provider):
    appliance = temp_appliance_for_cur_provider
    vm = VM.factory(appliance.vm_name, provider)
    provider.refresh_provider_relationships()
    vm.wait_to_appear()
    return vm


def do_scan(vm, additional_item_check=None):
    if vm.rediscover_if_analysis_data_present():
        # policy profile assignment is lost so reassign
        vm.assign_policy_profiles(*vm.assigned_policy_profiles)

    def _scan():
        return vm.get_detail(properties=("Lifecycle", "Last Analyzed")).lower()
    original = _scan()
    if additional_item_check is not None:
        original_item = vm.get_detail(properties=additional_item_check)
    vm.smartstate_scan(cancel=False, from_details=True)
    flash.assert_message_contain(version.pick({
        version.LOWEST: "Smart State Analysis initiated",
        "5.5": "Analysis initiated for 1 VM and Instance from the CFME Database"}))
    logger.info("Scan initiated")
    wait_for(
        lambda: _scan() != original,
        num_sec=600, delay=5, fail_func=lambda: toolbar.select("Reload"))
    if additional_item_check is not None:
        wait_for(
            lambda: vm.get_detail(properties=additional_item_check) != original_item,
            num_sec=120, delay=5, fail_func=lambda: toolbar.select("Reload"))
    logger.info("Scan finished")


def test_check_package_presence(request, fleecing_vm, analysis_profile):
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
    assert fleecing_vm.check_compliance()


def test_check_files(request, fleecing_vm, analysis_profile):
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
    assert fleecing_vm.check_compliance()


def test_compliance_with_unconditional_policy(host, assign_policy_for_testing):
    assign_policy_for_testing.assign_actions_to_event(
        "Host Compliance Check",
        {"Mark as Non-Compliant": True}
    )
    host.check_compliance()
    assert not host.is_compliant
