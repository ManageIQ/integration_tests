"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [test_requirements.automate, pytest.mark.manual]


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


@pytest.mark.tier(1)
def test_vm_naming_number_padding():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Automate
        tags: automate
        setup:
            1. Add any provider
        testSteps:
            1. Provision more than 10 VMs
        expectedResults:
            1. VMs should be generated with respective numbering

    Bugzilla:
        1688672
    """
    pass


@pytest.mark.tier(1)
def test_git_refresh_with_renamed_yaml():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        startsin: 5.10
        casecomponent: Automate
        testSteps:
            1. Have a git backed Automate Domain
            2. Delete (or rename) a .rb/.yaml pair, commit, push to repo
            3. Refresh Domain in CF ui
        expectedResults:
            1.
            2.
            3. Domain should refresh successfully and renamed method appears

    Bugzilla:
        1716443
    """
    pass


@pytest.mark.tier(2)
def test_git_refresh_with_rapid_updates():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        startsin: 5.10
        casecomponent: Automate
        testSteps:
            1. Have a git backed domain that imported cleanly
            2. Break the domain in Git, or notice a method isn't visible because its matching .yaml
               was never added to git
            3. Add an broken .yaml to git, push, etc, in a desperate attempt to fix the issue.
               Note: There are different .yaml files for domain, namespace, class etc. So to break
               this file; you can change file name from __domain__.yaml to __testdomain__.yaml(or
               any) or you can change the code in the .yaml file
            4. Go to CF UI, Automate, Domain, "Refresh with a new branch or tag"
            5. Select suitable branch and "Save"
            6. Check evm.log
            7. Fix e.g. <method>.yaml, commit, push
            8. Refresh page you never left
        expectedResults:
            1.
            2.
            3.
            4.
            5. Error message should be displayed in UI
            6. Errors should be available in logs
            7.
            8. It should re-pull or force user to do something if (5) is updated to block

    Bugzilla:
        1696396
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1713072, 1745197])
def test_automate_task_schedule():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        setup:
            1. Create domain, namespace, class and instance
            2. Also create automate method with below ruby code:
                >> $evm.log(:info, "Hello World")
        testSteps:
            1. Go to Configuration > Settings > Zones > Schedules
            2. Create schedule with required fields:
               >> Action - Automation Tasks
               >> Object Details(Request) - Call_Instance
               >> Attribute/Value Pairs
                     >> domain - domain_name
                     >> namespace - namespace_name
                     >> class - class_name
                     >> instance - instance_name
               >> Timer Options
            3. Check automation logs
        expectedResults:
            1.
            2.
            3. Automate method should be executed on scheduled time.

    Bugzilla:
        1713072
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1743227])
def test_queue_up_schedule_run_now():
    """
    Bugzilla:
        1743227

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Navigate to configuration > Settings > Schedules > Select "Add a new schedule"
            2. Fill the name, description then select Action - "Automation task"
            3. Select time options
            4. Click on add button
            5. Click on created schedule and select option - "Queue up this schedule to run now"
            6. See automation logs
        expectedResults:
            1.
            2.
            3.
            4.
            5. Schedule should run forcefully
            6. Task related automation logs should generate
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1741259])
def test_copy_automate_method_without_edit():
    """
    Bugzilla:
        1741259

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Navigate to Automation > Automate > Explorer
            2. Select a method from the datastore
            3. Try to copy and paste some code from the method without entering the edit mode
        expectedResults:
            1.
            2.
            3. You should be able to copy the highlighted text
    """
    pass
