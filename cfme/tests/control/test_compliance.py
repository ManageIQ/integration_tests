# -*- coding: utf-8 -*-
import diaper
import fauxfactory
import pytest
from wrapanapi import VmState

from . import do_scan
from cfme import test_requirements
from cfme.control.explorer.conditions import VMCondition
from cfme.control.explorer.policies import HostCompliancePolicy
from cfme.control.explorer.policies import VMCompliancePolicy
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import conf
from cfme.utils.blockers import BZ
from cfme.utils.update import update

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
    return provider.hosts.all()[0]


@pytest.fixture
def policy_for_testing(policy_name, policy_profile_name, provider, policy_collection,
        policy_profile_collection):
    policy = policy_collection.create(HostCompliancePolicy, policy_name)
    policy_profile = policy_profile_collection.create(policy_profile_name, policies=[policy])
    yield policy
    policy_profile.delete()
    policy.delete()


@pytest.fixture
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
        minor = "0"
    vddk_version = "v{}_{}".format(major, minor)
    # cf. BZ 1651702 vddk_version 6_7 does not currently work with CFME, so use v6_5
    if BZ(1651702, forced_streams=['5.9', '5.10']).blocks:
        vddk_version = "v6_5"
    url = conf.cfme_data.get("basic_info").get("vddk_url").get(vddk_version)
    if url is None:
        pytest.skip("There is no vddk url for this VMware provider version")
    else:
        return url


@pytest.fixture(scope="module")
def configure_fleecing(appliance, provider, setup_provider_modscope, vddk_url):
    provider.setup_hosts_credentials()
    appliance.install_vddk(vddk_url=vddk_url)
    yield
    appliance.uninstall_vddk()
    provider.remove_hosts_credentials()


@pytest.fixture(scope="module")
def compliance_vm(configure_fleecing, provider, full_template_modscope):
    name = "{}-{}".format("test-compliance", fauxfactory.gen_alpha(4))
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(name, provider, full_template_modscope.name)
    vm.create_on_provider(allow_skip="default")
    vm.mgmt.ensure_state(VmState.RUNNING)
    if not vm.exists:
        vm.wait_to_appear(timeout=900)
    yield vm
    vm.cleanup_on_provider()
    provider.refresh_provider_relationships()


@pytest.fixture(scope="module")
def analysis_profile(appliance):
    ap = appliance.collections.analysis_profiles.instantiate(
        name="default",
        description="ap-desc",
        profile_type=appliance.collections.analysis_profiles.VM_TYPE,
        categories=["Services", "User Accounts", "Software", "VM Configuration", "System"]
    )
    if ap.exists:
        ap.delete()
    appliance.collections.analysis_profiles.create(
        name="default",
        description="ap-desc",
        profile_type=appliance.collections.analysis_profiles.VM_TYPE,
        categories=["Services", "User Accounts", "Software", "VM Configuration", "System"]
    )
    yield ap
    if ap.exists:
        ap.delete()


def test_check_package_presence(request, compliance_vm, analysis_profile, policy_collection,
        policy_profile_collection, condition_collection):
    """This test checks compliance by presence of a certain "kernel" package which is expected
    to be present on the full_template.

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
    """
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

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
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


def test_compliance_with_unconditional_policy(host, assign_policy_for_testing):
    """
    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
    """
    assign_policy_for_testing.assign_actions_to_event(
        "Host Compliance Check",
        {"Mark as Non-Compliant": True}
    )
    host.check_compliance()
    assert not host.is_compliant
