# -*- coding: utf-8 -*-
import diaper
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.control.explorer.policies import VMCompliancePolicy, HostCompliancePolicy
from cfme.control.explorer.conditions import VMCondition
from cfme.control.explorer.policy_profiles import PolicyProfile
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.configure.configuration import AnalysisProfile
from utils import testgen
from utils.hosts import setup_providers_hosts_credentials
from utils.update import update
from cfme import test_requirements
from . import do_scan, vddk_url_map


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles=["+automate", "+smartstate", "+smartproxy"]),
    pytest.mark.tier(3),
    test_requirements.control
]


pytest_generate_tests = testgen.generate([VMwareProvider], scope="module")


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
def configure_fleecing(appliance, has_no_providers_modscope, provider, setup_provider_modscope):
    setup_providers_hosts_credentials(provider.key)
    appliance.install_vddk(reboot=True, vddk_url=vddk_url_map[str(provider.version)])
    appliance.reboot()
    appliance.browser.quit_browser()
    yield
    appliance.uninstall_vddk()


@pytest.yield_fixture(scope="module")
def compliance_vm(configure_fleecing, provider, full_template_modscope):
    name = "{}-{}".format("test-compliance", fauxfactory.gen_alpha(4))
    vm = VM.factory(name, provider, template_name=full_template_modscope["name"])
    vm.create_on_provider(allow_skip="default")
    provider.mgmt.start_vm(vm.name)
    provider.mgmt.wait_vm_running(vm.name)
    if not vm.exists:
        vm.wait_to_appear(timeout=900)
    yield vm
    if provider.mgmt.does_vm_exist(vm.name):
        provider.mgmt.delete_vm(vm.name)
    provider.refresh_provider_relationships()


@pytest.yield_fixture(scope="module")
def analysis_profile():
    ap = AnalysisProfile(
        name="default",
        description="ap-desc",
        profile_type="VM",
        categories=[
            "check_services",
            "check_accounts",
            "check_software",
            "check_vmconfig",
            "check_system"
        ]
    )
    if ap.exists:
        ap.delete()
    ap.create()
    yield ap
    ap.delete()


def test_check_package_presence(request, compliance_vm, analysis_profile):
    """This test checks compliance by presence of a certain "kernel" package which is expected
    to be present on the full_template."""
    condition = VMCondition(
        "Compliance testing condition {}".format(fauxfactory.gen_alphanumeric(8)),
        expression=("fill_find(field=VM and Instance.Guest Applications : Name, "
            "skey=STARTS WITH, value=kernel, check=Check Count, ckey= = , cvalue=1)")
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    condition.create()
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
    compliance_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: compliance_vm.unassign_policy_profiles(profile.description))
    do_scan(compliance_vm)
    assert compliance_vm.check_compliance()


def test_check_files(request, compliance_vm, analysis_profile):
    """This test checks presence and contents of a certain file. Due to caching, an existing file
    is checked.
    """
    check_file_name = "/etc/hosts"
    check_file_contents = "127.0.0.1"
    condition = VMCondition(
        "Compliance testing condition {}".format(fauxfactory.gen_alphanumeric(8)),
        expression=("fill_find(VM and Instance.Files : Name, "
            "=, {}, Check Any, Contents, INCLUDES, {})".format(
                check_file_name, check_file_contents))
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    condition.create()
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
    compliance_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: compliance_vm.unassign_policy_profiles(profile.description))

    with update(analysis_profile):
        analysis_profile.files = [(check_file_name, True)]

    do_scan(compliance_vm, ("Configuration", "Files"))
    assert compliance_vm.check_compliance()


def test_compliance_with_unconditional_policy(host, assign_policy_for_testing):
    assign_policy_for_testing.assign_actions_to_event(
        "Host Compliance Check",
        {"Mark as Non-Compliant": True}
    )
    host.check_compliance()
    assert not host.is_compliant
