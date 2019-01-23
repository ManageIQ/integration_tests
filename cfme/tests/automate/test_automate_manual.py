"""Manual tests"""

import pytest

pytestmark = [pytest.mark.ignore_stream("5.9", "5.10", "upstream")]


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_domain_import_top_level_directory():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1389823 Importing domain
    from git should work with or without the top level domain directory.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_quota_source_user():
    """
    When copying and modifying
    /System/CommonMethods/QuotaStateMachine/quota to user the user as the
    quota source and when the user is tagged, the quotas are in effect.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_simulate_retry():
    """
    PR Link
    Automate simulation now supports simulating the state machines.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
        setup: Create a state machine that contains a couple of states from which one
               of them retries at least once.
        startsin: 5.6
        testSteps:
            1. Use automate simulation UI to call the state machine (Call_Instance)
        expectedResults:
            1. A Retry button appears.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_customize_request_security_group():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1335989

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_import_multiple_domains():
    """
    Import of multiple domains from a single git repo is not allowed

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_relationship_trailing_spaces():
    """
    PR Link (Merged 2016-04-01)
    Handle trailing whitespaces in automate instance relationships.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/10h
        setup: A fresh appliance.
        startsin: 5.6
        testSteps:
            1. Create a class and its instance, also create second one,
               that has a relationship field. Create an instance with the
               relationship field pointing to the first class" instance but
               add a couple of whitespaces after it.
            2. Execute the AE model, eg. using Simulate.
        expectedResults:
            1.
            2. Logs contain no resolution errors
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_generic_object_service_associations():
    """
    Use the attached domain to test this bug:
    1) Import end enable the domain
    2) Have at least one service created (Generic is enough)
    3) Run rails console and create the object definition:
    GenericObjectDefinition.create(
    :name => "LoadBalancer",
    :properties => {
    :attributes   => {:location => "string"},
    :associations => {:vms => "Vm", :services => "Service"},
    }
    )
    4) Run tail -fn0 log/automation.log | egrep "ERROR|XYZ"
    5) Simulate Request/GOTest with method execution
    In the tail"ed log:
    There should be no ERROR lines related to the execution.
    There should be these two lines:
    <AEMethod gotest> XYZ go object: #<MiqAeServiceGenericObject
    ....something...>
    <AEMethod gotest> XYZ load balancer got service:
    #<MiqAeServiceService:....something....>
    If there is "XYZ load balancer got service: nil", then this bug was
    reproduced.
    thx @lfu

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_automate_git_domain_displayed_in_dialog():
    """
    Check that the domain imported from git is displayed and usable in the
    pop-up tree in the dialog editor.
    You can use eg. https://github.com/ramrexx/CloudForms_Essentials.git
    for that

    Polarion:
        assignee: ghubale
        casecomponent: automate
        initialEstimate: 1/15h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_disabled_domains_in_domain_priority():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1331017 When the admin
    clicks on a instance that has duplicate entries in two different
    domains. If one domain is disabled it is still displayed in the UI for
    the domain priority.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_engine_database_connection():
    """
    All steps in: https://bugzilla.redhat.com/show_bug.cgi?id=1334909

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_check_quota_regression():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1554989
    Update from 5.8.2 to 5.8.3 has broken custom automate method.  Error
    is thrown for the check_quota instance method for an undefined method
    provisioned_storage.
    You"ll need to create an invalid VM provisioning request to reproduce
    this issue.
    The starting point is an appliance with a provider configured, that
    can successfully provision a VM using lifecycle provisioning.
    1. Add a second provider to use for VM lifecycle provisioning.
    2. Add a 2nd zone called "test_zone". (Don"t add a second appliance
    for this zone)
    3. Set the zone of the second provider to be "test_zone".
    4. Provision a VM for the second provider, using VM lifecycle
    provisioning. (The provisioning request should remain in
    pending/active status and should not get processed because there is no
    appliance/workers for the "test_zone".)
    5. Delete the template used in step 4.(Through the UI when you
    navigate to virtual machines, templates is on the left nav bar, select
    the template used in step 4 and select: "Remove from Inventory"
    6. Provisioning a VM for the first provider, using VM lifecycle
    provisioning should produce the reported error.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_domain_import_with_no_connection():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1391208

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_schema_field_without_type():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1365442
    It shouldn"t be possible to add a field without specifying a type.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_retry_onexit_increases():
    """
    To reproduce:
    1) Import the attached file, it will create a domain called
    OnExitRetry
    2) Enable the domain
    3) Go to Automate / Simulation
    4) Simulate Request with instance OnExitRetry, execute methods
    5) Click submit, open the tree on right and expand ae_state_retries
    It should be 1 by now and subsequent clicks on Retry should raise the
    number if it works properly.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_simulation_result_has_hash_data():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1445089
    The UI should display the result objects if the Simulation Result has
    hash data.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_import_without_master():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1508881
    Git repository doesn"t have to have master branch

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_state_machine_variable():
    """
    Test whether storing the state machine variable works and the vaule is
    available in another state.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_automate_method_copy():
    """
    Should copy selected automate method/Instance without going into edit
    mode.
    Steps:
    1. Add new domain (In enabled/unlock mode)
    2. Add namespace in that domain
    3. Add class in that namespace
    4. Unlock ManageIQ domain now
    5. Select Instance/Method from any class in ManageIQ
    6. From configuration toolbar, select `Copy this method/Instance`
    Additional info: https://bugzilla.redhat.com/show_bug.cgi?id=1500956

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_custom_button_disable():
    """
    Check if the button is disable or not (i.e. visible but blurry)
    Steps
    1)Add Button Group
    2)Add a button to the newly created button group
    3)Add an expression for disabling button (can use simple {"tag":
    {"department":"Support"}} expression)
    4)Add the Button group to a page
    5)Check that button is enabled; if enabled pass else fail.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_import_deleted_tag():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1394194

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_service_quota_runs_only_once():
    """
    Steps described here:
    https://bugzilla.redhat.com/show_bug.cgi?id=1317698

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_state_method():
    """
    PR link (merged 2016-03-24)
    You can pass methods as states compared to the old method of passing
    instances which had to be located in different classes. You use the
    METHOD:: prefix

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
        setup: A fresh appliance.
        startsin: 5.6
        testSteps:
            1. Create an automate class that has one state.
            2. Create a method in the class, make the method output
               something recognizable in the logs
            3. Create an instance inside the class, and as a Value for the
               state use: METHOD::method_name where method_name is the name
               of the method you created
            4. Run a simulation, use Request / Call_Instance to call your
               state machine instance
        expectedResults:
            1. Class created
            2. Method created
            3. Instance created
            4. The method got called, detectable by grepping logs
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_button_can_trigger_events():
    """
    In the button creation dialog there must be MiqEvent available for
    System/Process entry.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/60h
        startsin: 5.6.1
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_requests_tab_exposed():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1508490
    Need to expose Automate => Requests tab from the Web UI without
    exposing any other Automate tabs (i.e. Explorer, Customization,
    Import/Export, Logs). The only way to expose this in the Web UI, is to
    enable Services => Requests, and at least one tab from the Automate
    section (i.e. Explorer, Customization, etc).

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_credentials_changed():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1552274

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_git_import_case_insensitive():
    """
    bin/rake evm:automate:import PREVIEW=false
    GIT_URL=https://github.com/mkanoor/SimpleDomain REF=test2branch
    This should not cause an error (the actual name of the branch is
    Test2Branch).

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_custom_button_enable():
    """
    Check if the button is enabled or not
    Steps
    1)Add Button Group
    2)Add a button to the newly created button group
    3)Add an expression for enabling button
    4)Add the Button group to a page
    5)Check that button is enabled; if enabled pass else fail.

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_assert_failed_substitution():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1335669

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_import_namespace_attributes_updated():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1440226 1. Export an
    Automate model
    2. Change the display name and description in the exported namespace
    yaml file
    3. Run an import with the updated data
    4. Check if the namespace attributes get updated.Display name and
    description attributes should get updated

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_user_has_groups():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1411424
    This method should work:  groups = $evm.vmdb(:user).first.miq_groups
    $evm.log(:info, "Displaying the user"s groups: #{groups.inspect}")

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_quota_units():
    """
    Steps described here:
    https://bugzilla.redhat.com/show_bug.cgi?id=1334318

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_restrict_domain_crud():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1365493
    When you create a role that can only view automate domains, it can
    view automate domains, it cannot manipulate the domains themselves,
    but can CRUD on namespaces, classes, instances ....

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_custom_button_visibility():
    """
    This test is required to test the visibility option in the customize
    button.
    Steps
    1)Create Button Group
    2)Create a Button for the button group
    3)Add the Button group to a page
    4)Make write a positive visibility expression
    5)If button is visible and clickable then pass else fail

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_embedded_method():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1523379
    For a "new" method when adding Embedded Methods the UI hangs in the
    tree view when the method is selected

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_verify_ssl():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1470738

    Polarion:
        assignee: ghubale
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass
