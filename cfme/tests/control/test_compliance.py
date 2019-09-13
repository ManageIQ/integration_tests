# -*- coding: utf-8 -*-
import diaper
import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.control.explorer.conditions import VMCondition
from cfme.control.explorer.policies import HostCompliancePolicy
from cfme.control.explorer.policies import VMCompliancePolicy
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.tests.control import do_scan
from cfme.utils.config_data import cfme_data
from cfme.utils.update import update

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles=["+automate", "+smartstate", "+smartproxy"]),
    pytest.mark.tier(3),
    test_requirements.control,
    pytest.mark.provider([VMwareProvider], scope='module'),
    pytest.mark.usefixtures("setup_provider_modscope")
]


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
def policy_for_testing(appliance, policy_name, policy_profile_name):
    policy = appliance.collections.policies.create(HostCompliancePolicy, policy_name)
    policy_profile = appliance.collections.policy_profiles.create(
        policy_profile_name, policies=[policy]
    )
    yield policy
    policy_profile.delete()
    policy.delete()


@pytest.fixture
def assign_policy_for_testing(policy_for_testing, host, policy_profile_name):
    host.assign_policy_profiles(policy_profile_name)
    yield policy_for_testing
    host.unassign_policy_profiles(policy_profile_name)


@pytest.fixture(scope="module")
def compliance_vm(configure_fleecing_modscope, provider, full_template_modscope):
    name = "{}-{}".format("test-compliance", fauxfactory.gen_alpha(4))
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(name, provider, full_template_modscope.name)
    # TODO: remove this check once issue with SSA on other hosts in vSphere 6.5 is figured out
    if provider.version == 6.5:
        vm.create_on_provider(
            allow_skip="default",
            host=cfme_data['management_systems'][provider.key]['hosts'][0].name
        )
    else:
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


def test_check_package_presence(request, appliance, compliance_vm, analysis_profile):
    """This test checks compliance by presence of a certain "kernel" package which is expected
    to be present on the full_template.

    Metadata:
        test_flag: provision, policy

    Bugzilla:
        1730805

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Control
        caseimportance: high
    """
    condition = appliance.collections.conditions.create(
        VMCondition,
        "Compliance testing condition {}".format(fauxfactory.gen_alphanumeric(8)),
        expression=("fill_find(field=VM and Instance.Guest Applications : Name, "
            "skey=STARTS WITH, value=kernel, check=Check Count, ckey= = , cvalue=1)")
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = appliance.collections.policies.create(
        VMCompliancePolicy,
        "Compliance {}".format(fauxfactory.gen_alphanumeric(8))
    )
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.assign_conditions(condition)
    profile = appliance.collections.policy_profiles.create(
        "Compliance PP {}".format(fauxfactory.gen_alphanumeric(8)),
        policies=[policy]
    )
    request.addfinalizer(lambda: diaper(profile.delete))
    compliance_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: compliance_vm.unassign_policy_profiles(profile.description))
    do_scan(compliance_vm)
    compliance_vm.check_compliance()
    assert compliance_vm.compliant


def test_check_files(request, appliance, compliance_vm, analysis_profile):
    """This test checks presence and contents of a certain file. Due to caching, an existing file
    is checked.

    Metadata:
        test_flag: provision, policy

    Bugzilla:
        1730805

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Control
        caseimportance: high
    """
    check_file_name = "/etc/hosts"
    check_file_contents = "127.0.0.1"
    condition = appliance.collections.conditions.create(
        VMCondition,
        "Compliance testing condition {}".format(fauxfactory.gen_alphanumeric(8)),
        expression=("fill_find(VM and Instance.Files : Name, "
            "=, {}, Check Any, Contents, INCLUDES, {})".format(
                check_file_name, check_file_contents))
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = appliance.collections.policies.create(
        VMCompliancePolicy,
        "Compliance {}".format(fauxfactory.gen_alphanumeric(8))
    )
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.assign_conditions(condition)
    profile = appliance.collections.policy_profiles.create(
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

    Metadata:
        test_flag: policy

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
        caseimportance: high
    """
    assign_policy_for_testing.assign_actions_to_event(
        "Host Compliance Check",
        {"Mark as Non-Compliant": True}
    )
    host.check_compliance()
    assert not host.is_compliant
