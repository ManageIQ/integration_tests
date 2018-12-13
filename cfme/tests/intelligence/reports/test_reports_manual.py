# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""

import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream("5.9", "5.10", "upstream")]


@pytest.mark.manual
@test_requirements.report
def test_calculating_the_sum_of_a_value_in_a_consolidated_report():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1298298
    Steps to Reproduce:
    1. create a new report on vms & templates
    2. select os name, number of cpus, disk space and other nuerical
    values
    3. consolidate the report by os name and calculate the total of all
    the other value

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
        title: Calculating the sum of a value in a consolidated report
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_create_simple_aggregated_custom_report():
    """
    Create aggregate custom report.
    Eg: consolidate and aggregate data points into maximum, minimum,
    average, and total.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        title: Create simple aggregated custom report
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_should_generate_with_no_errors_in_logs():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1592480#c21

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/2h
        startsin: 5.9
        title: Reports should generate with no errors in logs
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_persistent_volumes():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1563861

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_import_invalid_file():
    """
    import invalid file like txt, pdf.
    Import yaml file with wrong data.
    Flash message should display if we import wrong file.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_create_and_run_custom_report_using_rbac():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1526058

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_reports_custom_tags():
    """
    Add custom tags to report
    1)add custom tags to appliance using black console
    ssh to appliance, vmdb; rails c
    use following commands
    cat = Classification.create_category!(name: "rocat1", description:
    "read_only cat 1", read_only: true)
    cat.add_entry(name: "roent1", description: "read_only entry
    1")2)Create new or Edit existing report and look for the tag category
    in list of columns.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_custom_conditional_filter_report():
    """
    Steps to Reproduce: ===================
    1. Create a service with one of the above naming conventions (vm-test
    ,My-Test)
    2. Have at least one VM in the service so the reporting will parse it
    3. Create a report with a conditional filter in it, such as:
    conditions: !ruby/object:MiqExpression exp: and: - IS NOT NULL: field:
    Vm.service-name - IS NOT NULL: field: Vm-ems_cluster_name 3. Run the
    report
    https://bugzilla.redhat.com/show_bug.cgi?id=1521167

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_the_columns_for_the_custom_attribute_should_have_their_values_in_report():
    """
    Steps to Reproduce:
    1. set a custom attribute on a VM with a space in the name
    2. set a custom attribute on a VM with a colon in the name
    3. Create a report with the VM name and the two custom attributes
    4. run the report
    https://bugzilla.redhat.com/show_bug.cgi?id=1553750

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        title: The columns for the custom attribute should have their values in report
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_report_import_export_widgets():
    """
    Import and  Export widgets

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/16h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_report_import_export_widgets():
    """
    Import and  Export widgets

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/16h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(3)
def test_import_duplicate_report():
    """
    This case tests appliance behaviour when a duplicate report is
    imported.
    Steps:
    1) Create a custom report.
    2) Go to Import/Export accordion and click on `Custom Reports`.
    3) Export the available report(newly created custom report from step
    1).
    4) Import the same exported yaml file.
    Expected Result:
    A flash message should appear: `Skipping Report (already in DB):
    [report_name]`

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_for_base_report_one_time_a_day():
    """
    Create schedule that runs report daily. Check it was ran successfully

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_copy_generate_report_provisioning_activity():
    """
    1.Copied the report "Provisioning Activity - by Requester" to
    "Provisioning Activity - by Requester-2"
    2.Executing the copied report, one can se the vaule "Administrator"
    for the field "Provision.Request : Approved By".
    If one later configures the Styling to:
    Style: if: Red Background = Administrador Light Background Starts With
    A
    https://bugzilla.redhat.com/show_bug.cgi?id=1402547

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_after_setting_certain_types_of_filters_filter_tab_should_be_accessible_and_editable():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1519809
    Steps to Reproduce:
    1.configure a report using a filter based on "EVM Custom Attributes:
    Name" and "EVM Custom Attributes: Value"
    2.
    3.
    Actual results:
    after saving changes, trying to edit the filter will result in the
    user looping and being unable to access the page. Attempts to access
    the report will also cause puma to consume all cpu on at least one
    thread

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        title: After setting certain types of filters filter tab should be
               accessible and editable
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_send_report():
    """
    Create schedule
    Send an E-mail" and add more than five users in the mailing list.
    Un-check "Send if Report is Empty" option and select the type of
    attachmentQueue up this Schedule

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(3)
def test_report_fullscreen_enabled():
    """
    Navigate to Intelligence > Reports
    (queue same report twice)
    1)Sucesful report generting [populated]
    Select Generating Report
    -check Configuration > Show Fullscreen Report is disabled
    Wait ~1minute and Select sucesfully generated report
    -check Configuration > Show Fullscreen Report is enabled
    Select Show Fullscreen Report
    -check report was shown in fullscreen
    2)Select report with no data for reporting, queue the report [blank]
    (queue same report twice)
    Select Generating Report
    -check Configuration > Show Fullscreen Report is disabled
    Wait ~1minute and Select sucesfully generated report
    -check Configuration > Show Fullscreen Report is disabled
    Navigate to Intelligence > Saved Reports
    3)Select group of [populated] reports
    In table, select one of reports
    -check Configuration > Show Fullscreen Report is enabled
    Select Show Fullscreen Report
    -check report was shown in fullscreen
    Select both of reports
    -check Configuration > Show Fullscreen Report is disabled
    4)Select group of [blank] reports
    In table, select one of reports
    -check Configuration > Show Fullscreen Report is disabled
    Select both of reports
    -check Configuration > Show Fullscreen Report is disabled

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_check_my_company_all_evm_groups_filter_from_reports_schedule():
    """
    Steps to Reproduce:
    1.Navigate to Cloud Intel → Reports.
    2.Click the Schedules accordion
    3.Add a New Schedule
    4.Under Report Selection →
    Try to select custom report In Filter drop downs that you want to
    schedule
    https://bugzilla.redhat.com/show_bug.cgi?id=1559323

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/16h
        startsin: 5.9
        title: Check My Company(All EVM Groups) filter from reports schedule
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_date_should_be_change_in_editing_reports_scheduled():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1446052
    Steps to Reproduce:
    1. Edit schedule report
    2. Under "Timer" Select "monthly"  every "month"
    3. Try to change "Starting Date"

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.3
        title: Date should be change In editing reports scheduled
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_report_export_import_run_custom_report():
    """
    Steps:1. generate a report from an affected custom report
    2. export the custom report
    3. import the custom report
    4. generate a new report of that custom reportall rows behave
    consistently
    https://bugzilla.redhat.com/show_bug.cgi?id=1498471

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_for_base_report_hourly():
    """
    Create schedule that runs report hourly during the day. Check it was
    ran successfully

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_report_secondary_display_filter_should_be_editable():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1565171
    Steps to Reproduce:
    1.Create report based on container images
    2. Select some fields for the report
    3. ON the filter tab add primary filter
    4. Add secondary filter
    5. try to edit the secondary filter.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        title: Report secondary (display) filter should be editable
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_edit_chargeback_for_projects_report():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1485006

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_import_export_report():
    """
    Import and export report

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        setup: Create or Identify appliance
               (no prerequisite or provider needed for this test)
        title: Import/Export report
        testSteps:
            1. Sign up to appliance
            2. Navigate to Cloud Intelligence > Reports
            3. Select any report and create its copy
            4. Locate newly created report in My Company > Custom
            5. Navigate to Import / Export
            6. Select Custom reports
            7. Select newly copied report and select Export
            8. Download the yaml file
            9. Locate exported report in My Company > Custom
            10. Delete exported report
            11. Navigate back to Import / Export
            12. Select Choose file
            13. Locate and select previously downloaded yaml file
            14. Select Upload
            15. Locate import report in My Company > Custom
            16. Sign out
        expectedResults:
            1.
            2.
            3.
            4. Verify that canned report was copied under new name
            5.
            6. Verify you"ve been redirected to Import / Export screen
            7. Verify that yaml file download was initiated
            8.
            9.
            10.
            11.
            12. Verify File upload screen was open
            13.
            14. Verify Imported report is now again available for Export
            15. Verify report is present
            16.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_report_custom_with_tag():
    """
    steps:
    1 Assign tag to VM, for example, departament tag,we have used
    "Discipline".
    2 Asign tag to Tenant, for example, departament tag, we have used
    "Discipline".
    3 Create report with base report "VMs and Instances" and the next
    fields: Name Departament tag.
    4 Create report with base report "Cloud Tenant" and the next fields:
    Name Departament tag.
    5 Generate the two reports.
    https://bugzilla.redhat.com/show_bug.cgi?id=1504086

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_schedule_add_from_report():
    """
    Add schedule from report queue

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_manage_report_menu_accordion_with_users():
    """
    Steps:
    1. Create a new report called report01
    2. Create a new user under EvmGroup-super_administrator called
    testuser
    3. "Edit Report Menus" and add the report01 under EvmGroup-
    super_administrator"s Provisioning -> Activities
    4. Login using testuser and navigate to Reports
    5. No report01 is under Provisioning -> Activities
    BZ: 1535023

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_generate_reports_after_upgrade():
    """
    Test generate reports after updating the appliance to release version
    from prior version.
    BZ LInk: 1464154

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_queue_tenant_quotas_report():
    """
    Test multiple possible Tenant Quota Report configurations

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/4h
        setup: Create or Identify appliance with one or more synced providers
        title: Queue Tenant Quotas Report
        testSteps:
            1. Sign in to appliance
            2. Navigate to Settings > Access control > Tenants > My Tenant > Manage quotas
            3. Turn on Allocated Virtual CPUs and set it up to 10
            4. Save new quota configuration
            5. Navigate to Cloud Intel > Reports > Reports > Tentant Quotas
            6. Queue Tenant Quotas report
            7. //Wait ~1 minute
            8.
            9.
            10. Navigate to Settings > Access control > Tenants > My Tenant > Manage quotas
            11. Turn off Allocated Virtual CPUs, turn on Allocated Memory in
                GB and set it up to 100
            12. Save new quota configuration
            13. Navigate to Cloud Intel > Reports > Reports > Tentant Quotas
            14. Queue Tenant Quotas report
            15. //Wait ~1 minute
            16.
            17.
            18. Navigate to Settings > Access control > Tenants > My Tenant > Manage quotas
            19. Turn on Allocated Virtual CPUs and set it up to 10, turn on
                Allocated Memory in GB and set it up to 100
            20. Save new quota configuration
            21. Navigate to Cloud Intel > Reports > Reports > Tentant Quotas
            22. Queue Tenant Quotas report
            23. //Wait ~1 minute
            24.
            25.
            26. Navigate to Settings > Access control > Tenants > My Tenant > Manage quotas
            27. Turn on all quotas and set them up adequate numbers
            28. Save new quota configuration
            29. Navigate to Cloud Intel > Reports > Reports > Tentant Quotas
            30. Queue Tenant Quotas report
            31. //Wait ~1 minute
            32.
            33.
            34. Sign out
        expectedResults:
            1.
            2.
            3.
            4. Verify that flash message "Quotas for Tenant were saved" is shown
            5.
            6.
            7. Verify that only Allocated Virtual CPUs row is present in report
            8. Verify that Count is unit in the report
            9. Verify that following columns are shown in report:
               Tenant Name         Quota Name         Total Quota
               In Use         Allocated         Available
            10.
            11.
            12. Verify that flash message "Quotas for Tenant were saved" is shown
            13.
            14.
            15. Verify that only Allocated Memory in GB row is present in report
            16. Verify that GB is unit in the report
            17. Verify that following columns are shown in report:
                Tenant Name         Quota Name         Total Quota
                In Use         Allocated         Available
            18.
            19.
            20. Verify that flash message "Quotas for Tenant were saved" is shown
            21.
            22.
            23. Verify that Allocated Virtual CPUs and Allocated Memory in
                GB rows are present in report
            24. Verify that both Count and GB units are used in the report
            25. Verify that following columns are shown in report:
                Tenant Name         Quota Name         Total Quota
                In Use         Allocated         Available
            26.
            27.
            28. Verify that flash message "Quotas for Tenant were saved" is shown
            29.
            30.
            31. Verify that all quotas are present in report
            32. Verify that both Count and GB units are used in the report
            33. Verify that following columns are shown in report:
                Tenant Name         Quota Name         Total Quota
                In Use         Allocated         Available
            34.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_custom_storage_fields():
    """
    Steps to Reproduce:
    1. Add cloud provider (Openstack) -> Go to Compute-> Clouds->
    Configuration-> Add new cloud provider.
    2. Generate Report -> Go to cloud intel -> Reports-> Configuration->
    Add new report.
    3. Report filters -> Configure Report Columns:
    Base the report on: Cloud Volumes
    Selected Fields:
    -- Cloud Tenant: Name
    --  VMs: Name
    --  VMs: Used Storage
    --  VMs  RAM Size
    --  Vms: Disk 1
    https://bugzilla.redhat.com/show_bug.cgi?id=1499553

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.3
    """
    pass
