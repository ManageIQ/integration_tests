# -*- coding: utf-8 -*-
import diaper
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.control.explorer.policies import HostCompliancePolicy, VMCompliancePolicy
from cfme.control.explorer.conditions import VMCondition
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.configure.configuration.analysis_profile import AnalysisProfile
from cfme.utils import conf
from cfme.utils.blockers import BZ
from cfme.utils.hosts import setup_providers_hosts_credentials
from cfme.utils.update import update
from cfme import test_requirements
from . import do_scan


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles=["+automate", "+smartstate", "+smartproxy"]),
    pytest.mark.tier(3),
    test_requirements.control,
    pytest.mark.provider([VMwareProvider], scope='module'),
]


@pytest.fixture(scope="module")
def policy_profile_collection(appliance):
    return appliance.collections.policy_profiles


@pytest.fixture(scope="module")
def policy_collection(appliance):
    return appliance.collections.policies


@pytest.fixture(scope="module")
def condition_collection(appliance):
    return appliance.collections.conditions


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
def policy_for_testing(policy_name, policy_profile_name, provider, policy_collection,
        policy_profile_collection):
    policy = policy_collection.create(HostCompliancePolicy, policy_name)
    policy_profile = policy_profile_collection.create(policy_profile_name, policies=[policy])
    yield policy
    policy_profile.delete()
    policy.delete()


@pytest.yield_fixture
def assign_policy_for_testing(policy_for_testing, host, policy_profile_name):
    host.assign_policy_profiles(policy_profile_name)
    yield policy_for_testing
    host.unassign_policy_profiles(policy_profile_name)


@pytest.fixture(scope="module")
def vddk_url(provider):
    try:
        major, minor = str(provider.version).split(".")
    except ValueError:
        major = str(provider.version)
        minor = 0
    vddk_version = "v{}_{}".format(major, minor)
    try:
        return conf.cfme_data.get("basic_info").get("vddk_url").get(vddk_version)
    except AttributeError:
        pytest.skip("There is no vddk url for this VMware provider version")


@pytest.yield_fixture(scope="module")
def configure_fleecing(appliance, provider, setup_provider_modscope, vddk_url):
    setup_providers_hosts_credentials(provider)
    appliance.install_vddk(vddk_url=vddk_url)
    yield
    appliance.uninstall_vddk()


@pytest.yield_fixture(scope="module")
def compliance_vm(configure_fleecing, provider, full_template_modscope):
    name = "{}-{}".format("test-compliance", fauxfactory.gen_alpha(4))
    vm = VM.factory(name, provider, template_name=full_template_modscope.name)
    vm.create_on_provider(allow_skip="default")
    provider.mgmt.start_vm(vm.name)
    provider.mgmt.wait_vm_running(vm.name)
    if not vm.exists:
        vm.wait_to_appear(timeout=900)
    yield vm
    vm.cleanup_on_provider()
    provider.refresh_provider_relationships()


@pytest.yield_fixture(scope="module")
def analysis_profile():
    ap = AnalysisProfile(
        name="default",
        description="ap-desc",
        profile_type=AnalysisProfile.VM_TYPE,
        categories=["Services", "User Accounts", "Software", "VM Configuration", "System"]
    )
    if ap.exists:
        ap.delete()
    ap.create()
    yield ap
    ap.delete()


def test_check_package_presence(request, compliance_vm, analysis_profile, policy_collection,
        policy_profile_collection, condition_collection):
    """This test checks compliance by presence of a certain "kernel" package which is expected
    to be present on the full_template."""
    condition = condition_collection.create(
        VMCondition,
        "Compliance testing condition {}".format(fauxfactory.gen_alphanumeric(8)),
        expression=("fill_find(field=VM and Instance.Guest Applications : Name, "
            "skey=STARTS WITH, value=kernel, check=Check Count, ckey= = , cvalue=1)")
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = policy_collection.create(
        VMCompliancePolicy,
        "Compliance {}".format(fauxfactory.gen_alphanumeric(8))
    )
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.assign_conditions(condition)
    profile = policy_profile_collection.create(
        "Compliance PP {}".format(fauxfactory.gen_alphanumeric(8)),
        policies=[policy]
    )
    request.addfinalizer(lambda: diaper(profile.delete))
    compliance_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: compliance_vm.unassign_policy_profiles(profile.description))
    do_scan(compliance_vm)
    compliance_vm.check_compliance()
    assert compliance_vm.compliant


def test_check_files(request, compliance_vm, analysis_profile, condition_collection,
        policy_collection, policy_profile_collection):
    """This test checks presence and contents of a certain file. Due to caching, an existing file
    is checked.
    """
    check_file_name = "/etc/hosts"
    check_file_contents = "127.0.0.1"
    condition = condition_collection.create(
        VMCondition,
        "Compliance testing condition {}".format(fauxfactory.gen_alphanumeric(8)),
        expression=("fill_find(VM and Instance.Files : Name, "
            "=, {}, Check Any, Contents, INCLUDES, {})".format(
                check_file_name, check_file_contents))
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = policy_collection.create(
        VMCompliancePolicy,
        "Compliance {}".format(fauxfactory.gen_alphanumeric(8))
    )
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.assign_conditions(condition)
    profile = policy_profile_collection.create(
        "Compliance PP {}".format(fauxfactory.gen_alphanumeric(8)),
        policies=[policy]
    )
    request.addfinalizer(lambda: diaper(profile.delete))
    compliance_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: compliance_vm.unassign_policy_profiles(profile.description))

    with update(analysis_profile):
        analysis_profile.files = [{"Name": check_file_name, "Collect Contents?": True}]

    do_scan(compliance_vm, ("Configuration", "Files"))
    compliance_vm.check_compliance()
    assert compliance_vm.compliant


@pytest.mark.uncollectif(BZ(1491576, forced_streams=['5.7']).blocks, 'BZ 1491576')
def test_compliance_with_unconditional_policy(host, assign_policy_for_testing):
    assign_policy_for_testing.assign_actions_to_event(
        "Host Compliance Check",
        {"Mark as Non-Compliant": True}
    )
    host.check_compliance()
    assert not host.is_compliant
