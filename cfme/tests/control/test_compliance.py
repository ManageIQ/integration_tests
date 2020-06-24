import diaper
import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.control.explorer.conditions import VMCondition
from cfme.control.explorer.policies import HostCompliancePolicy
from cfme.control.explorer.policies import VMCompliancePolicy
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.tests.control import do_scan
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log_validator import LogValidator
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
    return fauxfactory.gen_alphanumeric(35, start="compliance_testing: policy ")


@pytest.fixture
def policy_profile_name():
    return fauxfactory.gen_alphanumeric(43, start="compliance_testing: policy profile ")


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
    name = fauxfactory.gen_alpha(20, start="test-compliance-")
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(name, provider, full_template_modscope.name)
    # TODO: remove this check once issue with SSA on other hosts in vSphere 6.5 is figured out
    if provider.version == 6.5:
        vm.create_on_provider(
            allow_skip="default",
            host=conf.cfme_data['management_systems'][provider.key]['hosts'][0].name
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
        assignee: dgaikwad
        initialEstimate: 1/4h
        casecomponent: Control
        caseimportance: high
    """
    condition = appliance.collections.conditions.create(
        VMCondition,
        fauxfactory.gen_alphanumeric(40, start="Compliance testing condition "),
        expression=("fill_find(field=VM and Instance.Guest Applications : Name, "
            "skey=STARTS WITH, value=kernel, check=Check Count, ckey= = , cvalue=1)")
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = appliance.collections.policies.create(
        VMCompliancePolicy,
        fauxfactory.gen_alphanumeric(15, start="Compliance ")
    )
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.assign_conditions(condition)
    profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alphanumeric(20, start="Compliance PP "),
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
        assignee: dgaikwad
        initialEstimate: 1/4h
        casecomponent: Control
        caseimportance: high
    """
    check_file_name = "/etc/hosts"
    check_file_contents = "127.0.0.1"
    condition = appliance.collections.conditions.create(
        VMCondition,
        fauxfactory.gen_alphanumeric(40, start="Compliance testing condition "),
        expression=("fill_find(VM and Instance.Files : Name, "
            "=, {}, Check Any, Contents, INCLUDES, {})".format(
                check_file_name, check_file_contents))
    )
    request.addfinalizer(lambda: diaper(condition.delete))
    policy = appliance.collections.policies.create(
        VMCompliancePolicy,
        fauxfactory.gen_alphanumeric(15, start="Compliance ")
    )
    request.addfinalizer(lambda: diaper(policy.delete))
    policy.assign_conditions(condition)
    profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alphanumeric(20, start="Compliance PP "),
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
        assignee: dgaikwad
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


@pytest.fixture
def create_policy_profile(appliance, request):
    condition = appliance.collections.conditions.create(
        VMCondition,
        fauxfactory.gen_alphanumeric(40, start="Compliance testing condition "),
        expression="fill_tag(VM and Instance.My Company Tags : Service Level, Gold)",
    )
    request.addfinalizer(condition.delete)

    policy = appliance.collections.policies.create(
        VMCompliancePolicy, fauxfactory.gen_alphanumeric(15, start="Compliance ")
    )
    request.addfinalizer(policy.delete)

    policy.assign_conditions(condition)

    profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alphanumeric(20, start="Compliance PP "), policies=[policy]
    )
    request.addfinalizer(profile.delete)

    return profile


@pytest.mark.meta(automates=[1824811])
@pytest.mark.provider([CloudProvider], scope="module", selector=ONE)
def test_compliance_instance(create_policy_profile, create_vm, request):
    """
    Bugzilla:
        1824811

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/4h
        casecomponent: Control
        caseimportance: high
        setup:
            1. Create condition.
            2. Create policy with the condition.
            3. Create a policy profile with the policy.
            4. Create a cloud instance.
        testSteps:
            1. Assign policy profile to an instance.
            2. From Instance's All page, select the instance entity, click on Configuration
                and select 'Check Compliance of Last Known Configuration'.
        expectedResults:
            1. Policy profile must be assigned successfully.
            2. Compliance should be initiated for the instance.
    """
    instance = create_vm
    instance.assign_policy_profiles(create_policy_profile.description)
    request.addfinalizer(
        lambda: instance.unassign_policy_profiles(create_policy_profile.description)
    )

    with LogValidator(
        "/var/www/miq/vmdb/log/production.log", failure_patterns=[".*FATAL.*"]
    ).waiting(timeout=120):
        view = navigate_to(instance.parent, "All")
        view.entities.get_entity(name=instance.name, use_search=True).ensure_checked()
        view.toolbar.policy.item_select(
            "Check Compliance of Last Known Configuration", handle_alert=True
        )
        view.flash.assert_message(
            "Check Compliance initiated for 1 VM and Instance from the CFME Database"
        )
