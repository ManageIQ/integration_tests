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


@pytest.mark.tier(3)
@pytest.mark.manual('manualonly')
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
@pytest.mark.ignore_stream("5.10")
def test_vm_name_automate_method():
    """This test case will check redesign of vm_name automated method

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.11
        casecomponent: Automate
        tags: automate

    Bugzilla:
        1677573
    """
    pass


@pytest.mark.tier(1)
def test_dialog_element_values_passed_to_button():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        startsin: 5.10
        casecomponent: Automate
        testSteps:
            1. Import the attached automate domain and dialog exports in BZ - 1715396. The automate
               domain contains a method to populate the dynamic second element in the dialog.
            2. Install object_walker automate domain from https://github.com/pemcg/object_walker
            3. Add a custom button to a VM (or any) object. The button should use the newly imported
               BZ dialog, and should run object_walker when submitted (/System/Process: Request,
               Message: create, Request: object_walker)
            4. Click the custom button, and observe the dialog. The element 'Text Box 1' default
               value is empty, the dynamic element 'Text Box 2' has been dynamically populated.
               click on submit the button.
            5. Repeat step 4, but type some some value(like "aa") in element 'Text Box 1'.
               Submit the button.
            6. Repeat step 5, but now also amend the text dynamically entered into 'Text Box 2'
               (for example adding the string "also").
        expectedResults:
            1.
            2.
            3.
            4. Values passed through to object_walker - both element values should be passed:
               >> ~/object_walker_reader.rb | grep dialog
                     |    $evm.root['dialog_text_box_1'] =    (type: String)
                     |    $evm.root['dialog_text_box_2'] = The dynamic method ran at:
                     2019-05-30 09:42:40 +0100   (type: String)
            5. The value from both test boxes should be passed through object_walker:
                ~/object_walker_reader.rb -t 2019-05-30T09:43:25.558037 | grep dialog
                     |    $evm.root['dialog_text_box_1'] = aa   (type: String)
                     |    $evm.root['dialog_text_box_2'] = The dynamic method ran at:
                     2019-05-30 09:42:43 +0100   (type: String)
            6. Note that both element values are now passed through to object_walker:
                ~/object_walker_reader.rb | grep dialog
                     |    $evm.root['dialog_text_box_1'] = ccdd   (type: String)
                     |    $evm.root['dialog_text_box_2'] = The dynamic method also ran at:
                     2019-05-30 09:50:10 +0100   (type: String)Provision more than 10 VMs
    Bugzilla:
        1715396
        1717501
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
def test_simulation_copy_button():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        startsin: 5.10
        casecomponent: Automate
        testSteps:
            1. Go to Automation > Automate > Simulation
            2. Fill in any required fields to enable submit button and click on 'Submit'
            4. Change any field - for example 'Object Attribute'
            5. Select Copy button
        expectedResults:
            1. Copy button should be disabled
            2. Copy button should be enabled
            3.
            4.
            5. Copy button should be disabled until form is submitted

    Bugzilla:
        1630800
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1713072])
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
@pytest.mark.meta(coverage=[1693362])
def test_redhat_domain_sync_after_upgrade():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Either dump database of appliance with version X to appliance with version Y
               or upgrade the appliance
            2. grep 'domain version on disk differs from db version' /var/www/miq/vmdb/log/evm.log
            3. Check last_startup.txt file
        expectedResults:
            1.
            2. You should find this string in logs: RedHat domain version on disk differs from db
               version
            3. You should find this string in file: RedHat domain version on disk differs from db
               version

    Bugzilla:
        1693362
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1678135])
def test_variable_pass_successive_playbook():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        setup:
            1. Enable embedded ansible role
        testSteps:
            1. Add Ansible repo called billy -
               https://github.com/ManageIQ/integration_tests_playbooks
            2. Copy Export zip (Ansible_State_Machine_for_Ansible_stats3.zip ) to downloads
               directory(Zip file with description - 'Automate domain' is attached with BZ(1678135)
            3. Go to Automation/Automate Import/Export and import zip file
            4. Click on "Toggle All/None" and hit the submit button
            5. Go to Automation/Automate/Explorer and Enable the imported domain
            6. Make sure all the playbook methods have all the information (see if Repository,
               Playbook and Machine credentials have values), update if needed
            7. Import or create hello_world (simple ansible dialog with Machine credentials and
               hosts fields)
            8. Create a Generic service using the hello_world dialog and select instance
               'CatalogItemInitialization_jira24'(Note: This is the state machine which executes
               playbooks successively) then order service
            9. Run "grep dump_vars2 automation.log" from log directory
        expectedResults:
            1. Ansible repository added
            2.
            3.
            4. Domain imported
            5. Domain enabled
            6. Playbook method updated(if needed as mentioned in step)
            7. Ansible dialog created
            8. Generic service catalog item created
            9. Variables should be passed through successive playbooks and you should see logs like
               this(https://bugzilla.redhat.com/show_bug.cgi?id=1678135#c13)

    Bugzilla:
        1678135
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1678132])
def test_variable_pass_method_playbook():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        setup:
            1. Enable embedded ansible role
        testSteps:
            1. Add Ansible repo called billy -
               https://github.com/ManageIQ/integration_tests_playbooks
            2. Copy Export zip (Ansible_State_Machine_for_Ansible_stats3.zip ) to downloads
               directory(Zip file with description - 'Automate domain' is attached with BZ(1678135)
            3. Go to Automation/Automate Import/Export and import zip file
            4. Click on "Toggle All/None" and hit the submit button
            5. Go to Automation/Automate/Explorer and Enable the imported domain
            6. Make sure all the playbook methods have all the information (see if Repository,
               Playbook and Machine credentials have values), update if needed
            7. Import or create hello_world (simple ansible dialog with Machine credentials and
               hosts fields)
            8. Create a Generic service using the hello_world dialog and select instance
               'CatalogItemInitialization_jira23'(Note: This is the state machine which executes
               playbooks and inline method successively) then order service
            9. Run "grep dump_vars2 automation.log" from log directory
        expectedResults:
            1. Ansible repository added
            2.
            3.
            4. Domain imported
            5. Domain enabled
            6. Playbook method updated(if needed as mentioned in step)
            7. Ansible dialog created
            8. Generic service catalog item created
            9. Variables should be passed through successive playbooks and you should see logs like
               this(https://bugzilla.redhat.com/show_bug.cgi?id=1678132#c5)

    Bugzilla:
        1678132
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1753860])
def test_overwrite_import_domain():
    """
    Bugzilla:
        1753860

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Create custom domain, namespace, class, instance, method. Do not delete this domain.
            2. Navigate to automation > automate > import/export and export all classes and
               instances to a file
            3. Extract the file and update __domain__.yaml file of custom domain as below:
               >> description: test_desc
               >> enabled: false
            4. Compress this domain file and import it via UI.
        expectedResults:
            1.
            2.
            3.
            4. Description and enabled status of existing domain should update.
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1753586])
@pytest.mark.customer_scenario
def test_crud_imported_domains():
    """
    Bugzilla:
        1753586

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Export the appliance domain as a zip file
            2. Extracted the ManageIQ directory to a new dir on the local machine called
               Domain_Test02
            3. From within the new Domain_Test02 dir, edit the __domain__.yaml file so that the
               'name' attribute equals Domain_Test02
               NOTE: Do not change the 'source' attribute from 'system' to 'user' this time.
            4. Archived the new Domain_Test02 dir and upload to CloudForms Appliance
        expectedResults:
            1.
            2.
            3.
            4. The imported domains should be Custom Domains or these imported domains should gets
               deleted from db
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1753523])
def test_attribute_value_message():
    """
    Bugzilla:
        1753523

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Create domain, namespace, class and instance pointing to method
            2. Navigate to automate > automation > simulation page
            3. Fill values for attribute/value pairs of namespace, class, instance and add message
               attribute with any value and click on submit.
            4. See automation.log
        expectedResults:
            1.
            2.
            3.
            4. Custom message attribute should be considered with instance in logs
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1752875])
def test_existing_domain_child_override():
    """
    PR:
     https://github.com/ManageIQ/manageiq-ui-classic/pull/4912

    Bugzilla:
        1752875

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Create custom domain and copy class - "ManageIQ/System/Request"
            2. Lock this domain
            3. Navigate to Automation > automate > Import/export and click on "export all classes
               and instances to file"
            4. Go to custom domain and unlock it. Remove instance - "ManageIQ/System/Request/" and
               copy - "ManageIQ/System/Process/Request" (you can copy more classes or methods or
               instances) to custom domain and again lock the domain.
            5. Go to import/export page and click on 'choose file'. Select exported file and click
               on upload
            6. Select "Select domain you wish to import from:" - "custom_domain" and check Toggle
               All/None
            7. Click on commit button.
            8. Then navigate to custom domain and unlock it
            9. Perform step 5, 6 and 7(In this case, domain will get imported)
            10. Go to custom domain
        expectedResults:
            1.
            2.
            3. Datastores exported on local system in zip format
            4.
            5.
            6.
            7. You should see flash message: "Error: Selected domain is locked"
            8.
            9. Selected domain imported successfully
            10. You should see existing as well as imported namespace, class, instance or method
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


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1747159])
def test_retire_vm_automate():
    """
    Bugzilla:
        1747159

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        setup:
            1. Add infrastructure provider
            2. Provision VM
        testSteps:
            1. Create custom domain, namespace, class, instance pointing to automate method
            2. Add vm retire ruby code to automate method
            3. Execute this method via simulation
        expectedResults:
            1.
            2.
            3. VM should retire
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1672007])
def test_invoke_custom_automation():
    """
    Bugzilla:
        1672007

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Navigate to Control > explorer > actions
            2. Select 'add a new action' from configuration dropdown
            3. Add description and select 'Action Type' - Invoke custom automation
            4. Fill attribute value pairs and click on save
            5. Edit the created action and add new attribute value pair
            6. Remove that newly added attribute value pair before clicking on save and then click
               on save
        expectedResults:
            1.
            2.
            3.
            4.
            5. Save button should enable
            6. Action should be saved successfully
    """
    pass
