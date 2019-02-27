"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_git_domain_import_top_level_directory():
    """
    Importing domain from git should work with or without the top level domain directory.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        title: Test automate git domain import top level directory
        testSteps:
            1. Enable server role: git Repositories Owner
            2. Navigate to Automation > Automate > Import/Export
            3. Create a Git Repository with the contents of a domain directory without including
               the domain directory.
        expectedResults:
            1.
            2.
            3. Import should work with or without the top level domain directory.

    Bugzilla:
        1389823
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(2)
def test_quota_source_user():
    """
    When copying and modifying
    /System/CommonMethods/QuotaStateMachine/quota to user; the user as the
    quota source and when the user is tagged, the quotas are in effect.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        title: Test quota source user
        testSteps:
            1. Assign quota to user by automate method
            2. Also assign quota to user by tagging(more/less than automate quota method limit)
            3. Provision Vm exceeding assigned quota
            4. Check last message of request info or notification message
        expectedResults:
            1.
            2.
            3. Request should be denied with quota exceeded message
            4. Last message should contain, quota exceeded because of tagging quota limit
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_automate_simulate_retry():
    """
    Automate simulation now supports simulating the state machines.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.6
        casecomponent: Automate
        tags: automate
        title: Test automate simulate retry
        setup:
            1. Create a state machine that contains a couple of states
        testSteps:
            1. Create an Automate model that has a State Machine that can end in a retry
            2. Run a simulation to test the Automate Model from Step 1
            3. When the Automation ends in a retry, we should be able to resubmit the request
            4. Use automate simulation UI to call the state machine (Call_Instance)
        expectedResults:
            1.
            2.
            3.
            4. A Retry button should appear.

    Bugzilla:
        1299579
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_customize_request_security_group():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.6
        casecomponent: Automate
        tags: automate
        title: Test customize request security group
        testSteps:
            1. Copy the "customize request" method to a writable domain and modify the mapping
               setting from mapping = 0 to mapping = 1.
            2. Create a REST API call to provision an Amazon or OpenStack instance and pass the
               "security_group" value with the name in "additional_values" that you want to apply.
            3. Check the request that was created and verify that the security group was not applied
        expectedResults:
            1.
            2.
            3. Specified security group gets set.

    Bugzilla:
        1335989
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_git_import_multiple_domains():
    """
    Import of multiple domains from a single git repo is not allowed

    Polarion:
        assignee: ghubale
        initialEstimate: 1/12h
        caseimportance: medium
        caseposneg: negative
        testtype: functional
        startsin: 5.10
        casecomponent: Automate
        tags: automate
        title: Test automate git import multiple domains
        testSteps:
            1. Enable server role: git Repositories Owner
            2. Navigate to Automation > Automate > Import/Export
            3. Import multiple domains from a single git repository
        expectedResults:
            1.
            2.
            3. Import of multiple domains from a single git repo is not allowed
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_automate_relationship_trailing_spaces():
    """
    Handle trailing whitespaces in automate instance relationships.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/10h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.6
        casecomponent: Automate
        tags: automate
        title: Test automate relationship trailing spaces
        testSteps:
            1. Create a class and its instance, also create second one,
               that has a relationship field.
            2. Create an instance with the relationship field pointing to the first class"
               instance but add a couple of whitespaces after it.
            3. Execute the AE model, eg. using Simulate.
        expectedResults:
            1.
            2.
            3. Logs contain no resolution errors.

    PR:
        https://github.com/ManageIQ/manageiq/pull/7550
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_automate_generic_object_service_associations():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/10h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        title: Test automate generic object service associations
        testSteps:
            1. Use the attached domain to test this bug:
            2. Import end enable the domain
            3. Have at least one service created (Generic is enough)
            4. Run rails console and create the object definition:
               GenericObjectDefinition.create(:name => "LoadBalancer", :properties => {
               :attributes   => {:location => "string"}, :associations => {:vms => "Vm",
               :services => "Service"},})
            5. Run tail -fn0 log/automation.log | egrep "ERROR|XYZ"
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. Simulate Request/GOTest with method execution
               In the tail"ed log:
               There should be no ERROR lines related to the execution.
               There should be these two lines:
               <AEMethod gotest> XYZ go object: #<MiqAeServiceGenericObject....something...>
               <AEMethod gotest> XYZ load balancer got service:
               #<MiqAeServiceService:....something....>
               If there is "XYZ load balancer got service: nil", then this bug was reproduced.

    Bugzilla:
        1410920
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(2)
def test_automate_git_domain_displayed_in_dialog():
    """
    Check that the domain imported from git is displayed and usable in the
    pop-up tree in the dialog editor.
    You can use eg. https://github.com/ramrexx/CloudForms_Essentials.git
    for that

    Polarion:
        assignee: ghubale
        initialEstimate: 1/15h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        title: Test automate git domain displayed in dialog
        testSteps:
            1. Import domain given in step 2
            2. You can use eg. https://github.com/ramrexx/CloudForms_Essentials.git
        expectedResults:
            1.
            2. Check that the domain imported from git is displayed and usable in the pop-up tree
               in the dialog editor.
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_disabled_domains_in_domain_priority():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1331017 When the admin
    clicks on a instance that has duplicate entries in two different
    domains. If one domain is disabled it is still displayed in the UI for
    the domain priority.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/12h
        caseimportance: low
        caseposneg: negative
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        title: Test automate disabled domains in domain priority
        testSteps:
            1. create two domains
            2. attach the same automate code to both domains.
            3. disable one domain
            4. click on a instance and see domains displayed.
        expectedResults:
            1.
            2.
            3.
            4. CFME should not display disabled domains

    Bugzilla:
        1331017
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_automate_engine_database_connection():
    """
    All steps in: https://bugzilla.redhat.com/show_bug.cgi?id=1334909

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        title: Test automate engine database connection
        testSteps:
            1. Create a 'visibility' tag category, containing a single tag
            2. Run the attached script via the RESTful API to duplicate the tags in the category
            3. Observe the error
        expectedResults:
            1.
            2.
            3. No error

    Bugzilla:
        1334909
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_check_quota_regression():
    """
    Update from 5.8.2 to 5.8.3 has broken custom automate method.  Error
    is thrown for the check_quota instance method for an undefined method
    provisioned_storage.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/6h
        tags: automate
        testSteps:
            1. You"ll need to create an invalid VM provisioning request to reproduce this issue.
            2. The starting point is an appliance with a provider configured, that can successfully
               provision a VM using lifecycle provisioning.
            3. Add a second provider to use for VM lifecycle provisioning.
            4. Add a 2nd zone called "test_zone". (Don"t add a second appliance for this zone)
            5. Set the zone of the second provider to be "test_zone".
            6. Provision a VM for the second provider, using VM lifecycle provisioning.
               (The provisioning request should remain in pending/active status and should not get
               processed because there is no appliance/workers for the "test_zone".)
            7. Delete the template used in step
            8. Through the UI when you navigate to virtual machines, templates is on the left nav
               bar, select the template used in step 4 and select: "Remove from Inventory"
            9.Provisioning a VM for the first provider, using VM lifecycle provisioning should
               produce the reported error.
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8.
            9. No error

    Bugzilla:
        1554989
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_git_domain_import_with_no_connection():
    """

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/6h
        tags: automate
        startsin: 5.7
        testSteps:
            1. Import a Git Domain into Automate
            2. Server the connection to the GIT Server from the appliance
               (Disable VPN or some other trick)
            3. List all the Automate Domains using Automate-> Explorer
        expectedResults:
            1.
            2.
            3. The domain should be displayed properly

    Bugzilla:
        1391208
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_automate_retry_onexit_increases():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/8h
        tags: automate
        testSteps:
            1. Import the attached file, it will create a domain called OnExitRetry
            2. Enable the domain
            3. Go to Automate / Simulation
            4. Simulate Request with instance OnExitRetry, execute methods
            5. Click submit, open the tree on right and expand ae_state_retries
        expectedResults:
            1.
            2.
            3.
            4.
            5. It should be 1 by now and subsequent clicks on Retry should raise the
               number if it works properly.

    Bugzilla:
        1365442
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_simulation_result_has_hash_data():
    """
    The UI should display the result objects if the Simulation Result has
    hash data.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/6h
        tags: automate
        testSteps:
            1. Create a Instance under /System/Request called ListUser, update it so that it points
               to a ListUser Method
            2. Create ListUser Method under /System/Request, paste the Attached Method
            3. Run Simulation
        expectedResults:
            1.
            2.
            3. The UI should display the result objects

    Bugzilla:
        1445089
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_git_import_without_master():
    """
    Git repository doesn't have to have master branch

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        tags: automate
        testSteps:
            1. Create git repository with different default branch than master.
            2. Add some valid code, for example exported one.
            3. Navigate to Automation -> Automate -> Import/Export
            4. Enter credentials and hit the submit button.
        expectedResults:
            1.
            2.
            3.
            4. Domain was imported from git

    Bugzilla:
        1508881
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_state_machine_variable():
    """
    Test whether storing the state machine variable works and the value is
    available in another state.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        tags: automate
        testSteps:
            1. Test whether storing the state machine variable works and the value is available in
               another state.
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(2)
def test_automate_method_copy():
    """
    Should copy selected automate method/Instance without going into edit mode.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/8h
        tags: automate
        startsin: 5.9
        upstream: yes
        testSteps:
            1. Add new domain (In enabled/unlock mode)
            2. Add namespace in that domain
            3. Add class in that namespace
            4. Unlock ManageIQ domain now
            5. Select Instance/Method from any class in ManageIQ
            6. From configuration toolbar, select "Copy this method/Instance"
        expectedResults:
            1.
            2.
            3.
            4. Able to copy method with "Copy This Method" toolbar.

    Bugzilla:
        1500956
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_git_import_deleted_tag():
    """

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        tags: automate
        startsin: 5.7
        testSteps:
            1. Create a github-hosted repository containing a correctly formatted automate domain.
               This repository should contain two or more tagged commits.
            2. Import the git-hosted domain into automate. Note that the tags are visible to select
               from in the import dialog
            3. Delete the most recent tagged commit and tag from the source github repository
            4. In automate explorer, click on the domain and click Configuration -> Refresh with a
               new branch or tag
            5. Observe the list of available tags to import from
        expectedResults:
            1.
            2.
            3.
            4.
            5. The deleted tag should no longer be visible in the list of tags to refresh from

    Bugzilla:
        1394194
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_automate_service_quota_runs_only_once():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        tags: automate
        testSteps:
            1. Provision a service.
            2. Check the automation.log to see both quota checks, one for
               ServiceTemplateProvisionRequest_created,
               and ServiceTemplateProvisionRequest_starting.
        expectedResults:
            1.
            2. Quota executed once.

    Bugzilla:
        1317698
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_automate_state_method():
    """
    You can pass methods as states compared to the old method of passing
    instances which had to be located in different classes. You use the
    METHOD:: prefix

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        tags: automate
        startsin: 5.6
        setup: A fresh appliance.
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
@test_requirements.automate
@pytest.mark.tier(2)
def test_button_can_trigger_events():
    """
    In the button creation dialog there must be MiqEvent available for
    System/Process entry.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/60h
        tags: automate
        startsin: 5.6.1
        testSteps:
            1. Go to automate and copy the Class /ManageIQ/System/Process to your custom domain
            2. Create an instance named
               MiqEvent with a rel5 of : /System/Event/MiqEvent/Policy/${/#event_type}
            3. On the custom button provide the following details.
               * System/Process/   MiqEvent
               * Message    create
               * Request    vm_retire_warn
               * Attribute
               * event_type   vm_retire_warn
        expectedResults:
            1.
            2.
            3. The MiqEntry is present and triggering an event should work

    Bugzilla:
        1348605
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_requests_tab_exposed():
    """
    Need to expose Automate => Requests tab from the Web UI without
    exposing any other Automate tabs (i.e. Explorer, Customization,
    Import/Export, Logs). The only way to expose this in the Web UI, is to
    enable Services => Requests, and at least one tab from the Automate
    section (i.e. Explorer, Customization, etc).

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        tags: automate
        startsin: 5.10
        testSteps:
            1. Test this with the role EvmRole-support
            2. By default this role does not have access to the Automation tab in the Web UI.
            3. Copy this role to AA-EVMRole-support and add all of the Automate role features.
            4. Did not allow user to see Requests under Automate.
            5. Enabled all the Service => Request role features.
            6. This allows user to see the Automate => Requests.

        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. "Automate/Requests" tab can be exposed for a role without exposing "Service/Requests"
               tab

    Bugzilla:
        1508490
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_git_credentials_changed():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/6h
        tags: automate
        testSteps:
            1. Customer is using a private enterprise git repo.
            2. The original username was changed and upon a refresh, the customer noticed
               it did not update
            3. There was no message letting the user know there was a validation error
        expectedResults:
            1.
            2.
            3. There were no FATAL messages in the log if the credentials were changed

    Bugzilla:
        1552274
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_automate_git_import_case_insensitive():
    """
    bin/rake evm:automate:import PREVIEW=false
    GIT_URL=https://github.com/mkanoor/SimpleDomain REF=test2branch
    This should not cause an error (the actual name of the branch is
    Test2Branch).

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/8h
        tags: automate
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_custom_button_enable():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.9
        tags: automate
        testSteps:
            1. Add Button Group
            2. Add a button to the newly created button group
            3. Add an expression for enabling button
            4. Add the Button group to a page
            5. Check that button is enabled; if enabled pass else fail.
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_assert_failed_substitution():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        tags: automate

    Bigzilla:
        1335669
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_import_namespace_attributes_updated():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/12h
        tags: automate
        testSteps:
            1. Export an Automate model
            2. Change the display name and description in the exported namespace yaml file
            3. Run an import with the updated data
            4. Check if the namespace attributes get updated.Display name and description attributes
               should get updated

    Bugzilla:
        1440226
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_user_has_groups():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1411424
    This method should work:  groups = $evm.vmdb(:user).first.miq_groups
    $evm.log(:info, "Displaying the user"s groups: #{groups.inspect}")

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        tags: automate
        startsin: 5.8

    Bugzilla:
        1411424
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_quota_units():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/4h
        tags: automate

    Bugzilla:
        1334318
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_restrict_domain_crud():
    """
    When you create a role that can only view automate domains, it can
    view automate domains, it cannot manipulate the domains themselves,
    but can CRUD on namespaces, classes, instances ....

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/6h
        tags: automate

    Bugzilla:
        1365493
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_custom_button_visibility():
    """
    This test is required to test the visibility option in the customize
    button.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        tags: automate
        startsin: 5.9
        testSteps:
            1. Create Button Group
            2. Create a Button for the button group
            3. Add the Button group to a page
            4. Make write a positive visibility expression
            5. If button is visible and clickable then pass else fail
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_embedded_method():
    """
    For a "new" method when adding Embedded Methods the UI hangs in the
    tree view when the method is selected

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        tags: automate

    Bugzilla:
        1523379
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(3)
def test_automate_git_verify_ssl():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/12h
        tags: automate
        startsin: 5.7

    Bugzilla:
        1470738
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_automate_buttons_requests():
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/18h
        tags: automate
        testSteps:
            1. Navigate to Automate -> Requests
            2. Check whether these buttons are displayed: Reload, Apply , Reset, Default
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_check_system_request_calls_depr_configurationmanagement():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Automate
        tags: automate
        testSteps:
            1. Copy /System/Request/ansible_tower_job instance to new domain
            2. Run that instance using simulation
            3. See automation log

    Bugzilla:
        1615444
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_task_id_for_method_automation_log():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate
        testSteps:
            1. Add existing or new automate method to newly created domain
            2. Run that instance using simulation
            3. See automation log
        expectedResults:
            1.
            2.
            3. Task id should be included in automation log for method logs.

    Bugzilla:
        1592428
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_refresh_git_current_user():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate
        testSteps:
            1. created non-super user 'ganesh' along with default 'admin' user.
            2. Using admin user imported git repo.:
               'https://github.com/ramrexx/CloudForms_Essentials.git'
            3. Logged in with admin and refreshed domain- 'CloudForms_Essentials'.
               Then checked all tasks.
            4. Found user name 'admin' next to 'Refresh git repository'.
            5. Then checked instances in that domain by logging in with user 'ganesh' and 'admin'.
            6. Logged in with non-super user 'ganesh' and refreshed domain- 'CloudForms_Essentials'.
               Then checked all tasks.
            7. Found user name 'ganesh' next to 'Refresh git repository'.
            8. Then checked instances in that domain by logging in with user 'ganesh' and 'admin'.
        expectedResults:
            1.
            2.
            3.
            4.
            5. It shows that
               e.g. 'Automate Instance [Provisioning - Updated 2019-01-15 11:41:43 UTC by admin]'
            6.
            7.
            8. It shows that
               e.g. 'Automate Instance [Provisioning - Updated 2019-01-15 11:44:43 UTC by ganesh]'
               Hence, correct user that calls refresh automation domain from git branch is shown.
    Bugzilla:
        1592428
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_list_of_diff_vm_storages_via_rails():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate
        testSteps:
            1. vmware = $evm.vmdb('ems').find_by_name('vmware 6.5 (nested)') ;
            2. vm = vmware.vms.select { |v| v.name == 'ghubale-cfme510' }.first ;
            3. vm.storage
            4. vm.storages
        expectedResults:
            1.
            2.
            3. Returns only one storage
            4. Returns available storages

    Bugzilla:
        1574444
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_generate_widget_content_by_automate():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate
        testSteps:
            1. create a new widget and add this widget to dashboard
            2. Create automate method with below content:
                #
                # Description: generate widget content by calling shell command
                #
                cmd =("/var/www/miq/vmdb/bin/rails r
                      'MiqWidget.find_by_title(\"Migration Candidates\").queue_generate_content'")
                system(cmd)
                exit MIQ_OK
            3. Execute the automate method(by simulation) and check updated time of that widget
               on dashboard.
            4. Updated status changes once we trigger the generation of a widget content from
               Automate method.
            5. Or we can check widget status by executing following commands on rails console:
                >> MiqWidget.find_by_title("widget_name")
                >> service_miq_widget = MiqAeMethodService::MiqAeServiceMiqWidget.find(widget_id)
                >> service_miq_widget.queue_generate_content (this will do same what we did with
                   automate method)
        expectedResults:
            1.
            2.
            3. Updated time of that widget on dashboard should be changes to current time of update
               by automate method.
            4.
            5. Updated time of that widget on dashboard should be changes to current time of update
               by rails.

    Bugzilla:
        1445932
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_valid_names_of_domain_namespace():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate
        testSteps:
            1. Navigate to Automation> Automate> Explorer
            2. Try to create Domain with name `Dummy Domain` (I put space which is invalid)
            3. Should give proper flash message

    Bugzilla:
        1650071
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_method_for_log_and_notify():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate
        testSteps:
            1. Create an Automate domain or use an existing writeable Automate domain
            2. Create a new Automate Method
            3. In the Automate Method screen embed ManageIQ/System/CommonMethods/Utils/log_object
               you can pick this
               method from the UI tree picker
            4. In your method add a line akin to
               ManageIQ::Automate::System::CommonMethods::Utils::LogObject.log_and_notify
               (:info, "Hello Testing Log & Notify", $evm.root['vm'], $evm)
            5. Check the logs
            6. In your UI session you should see a notification

    PR:
        https://github.com/ManageIQ/manageiq-content/pull/423
    """
    pass


@pytest.mark.manual
@test_requirements.automate
@pytest.mark.tier(1)
def test_miq_stop_abort_with_state_machines():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate

    Bugzilla:
        1441353
    """
    pass
