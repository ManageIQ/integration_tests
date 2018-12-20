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
