# -*- coding: utf-8 -*-
"""Manual tests"""

import pytest

from cfme import test_requirements


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
        setup:
            1. SSH into the appliance and vmdb
            2. Clone gist: https://gist.github.com/87dddcfbd549b03099f8e55f632b2b57.git
            3. Run: bin/rails r bz_1592480_db_replication_script.rb
            4. Run: bin/rails c.
            5. Execute:
                irb> r = MiqReport.where(:name => "BZ 1592480 Example Report").first
                irb> puts Benchmark.measure { r.queue_generate_table(:report_sync => true) }
            6. Log into the appliance.
            7. Navigate to Cloud Intel > Reports > Saved Reports
        testSteps:
            1. Locate the newly created report.
        expectedResults:
            1. Report must be accessible.
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
        setup:
            1. Add ocp39-hawk provider, or any other provider that has persistent volumes
            (use provider.mgmt.list_persistent_volumes() to see if a provider has it).
            2. Create a report based on Persistent Volumes, with Capacity and Storage Capacity
            columns.
            3. Queue the report.
        testSteps:
            1. Check the report columns.
        expectedResults:
            1. Values for Capacity must not be in hash(key:value pair) format.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_import_invalid_file():
    """
    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
        setup:
            1. Navigate to Cloud > Intel > Reports > Import / Export > Custom Reports
        testSteps:
            1. Import invalid file like txt, pdf.
            2. Import yaml file with wrong data.
        expectedResults:
            1. Flash message:`Error: the file uploaded is not of the supported format`
            should be displayed.
            2. Flash message:`Error: the file uploaded is not of the supported format`
            should be displayed.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_custom_conditional_filter_report():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1521167

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
        setup:
            1. Create a service with one of the above naming conventions (vm-test,My-Test)
            2. Have at least one VM in the service so the reporting will parse it
            3. Create a report with a conditional filter in it, such as:
                conditions: !ruby/object:MiqExpression exp: and: - IS NOT NULL: field:
                Vm.service-name - IS NOT NULL: field: Vm-ems_cluster_name.
        testSteps:
            1. Queue the report.
        expectedResults:
            1. Report must be generated successfully.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_report_import_export_widgets():
    """

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/16h
        startsin: 5.3
        setup:
            1. Navigate to Cloud Intel > Reports > Edit Report Menus > Import/Export > Widgets.
        testSteps:
            1. Export the widget in available widgets.
            2. Make some changes to the exported widget yaml and import it back.
        expectedResults:
            1. Widget must be exported successfully.
            2. Widget must be imported successfully.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(3)
def test_import_duplicate_report():
    """
    This case tests appliance behavior when a duplicate report is imported.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: None
        setup:
            1. Create a custom report.
            2. Go to Import/Export accordion and click on `Custom Reports`.
            3. Export the available report(newly created custom report from step
        testSteps:
            1. Import the same exported yaml file.
        expectedResults:
            1. A flash message should appear: `Skipping Report (already in DB):
            [report_name]`
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_for_base_report_one_time_a_day():
    """
    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
        setup:
            1. Navigate to Cloud Intel > Reports > All Schedules.
            2. Click on `Configuration` and select `Add a new Schedule`.
        testSteps:
            1. Create schedule that runs report daily.
        expectedResults:
            1. Schedule must run successfully.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_after_setting_certain_types_of_filters_filter_tab_should_be_accessible_and_editable():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1519809

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        title: After setting certain types of filters filter tab should be
                accessible and editable
        setup:
            1. Navigate to Cloud Intel > Reports > All Reports.
            2. Click on `Configuration` and select `Add a new Report`.
            3. Add a report using a filter based on "EVM Custom Attributes:
            Name" and "EVM Custom Attributes: Value".
            4. Edit the report.
        testSteps:
            1. Try editing the filter.
        expectedResults:
            1. Editing the filter should not result in screen freeze.
            Report must be accessible without causing puma consumption of all cpu on at least one
            thread.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_send_report():
    """
    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
        setup:
            1. Navigate to Cloud > Intel > Reports > Schedules.
            2. Click on `Configuration` and select `Add a new Schedule`.
        testSteps:
            1. Create schedule that send an email to more than five users.
            Un-check "Send if Report is Empty" option.
            2. Queue up this Schedule
        expectedResults:
            1. Schedule must be created successfully.
            2. Queueing the schedule must send the report via email to all the users.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(3)
def test_report_fullscreen_enabled():
    """
    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: low
        initialEstimate: 1/12h
        setup:
            1. Navigate to Cloud > Intel > Reports > All Reports
        testSteps:
            1. Select a report that would generate a populated report on queueing.
                Queue it, navigate to it's `Details` page, click on Configuration and check the `Show Fullscreen Report` option.
            2. Select a report that would generate an empty report on queueing.
                Queue it, navigate to it's `Details` page, click on Configuration and check the `Show Fullscreen Report` option.
        expectedResults:
            1. `Show Fullscreen Report` option is Enabled.
            2. `Show Fullscreen Report` option is Disabled.

    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_date_should_be_change_in_editing_reports_scheduled():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1446052

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.3
        title: Date should be change In editing reports scheduled
        setup:
            1. Create a report schedule which runs once.
            2. Select the schedule and edit it.
        testSteps:
            1. Under "Timer" Select "monthly"  every "month"
            2. Try to change "Starting Date"
        expectedResults:
            1. "Timer" must change accordingly.
            2. "Starting Date" must change accordingly.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_report_export_import_run_custom_report():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1498471

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.3
        setup:
            1. Create a custom report and queue it.
            2. Navigate to Import/Export > Custom Reports
        testSteps:
            1. Export the custom report.
            2. Make some minor change to the exported report yaml(e.g. change report name)
            and import the custom report again.
            3. Queue a new report from the imported custom report.
            Check if all the rows behave consistently.
        expectedResults:
            1. The report must be exported successfully.
            2. Report must be imported successfully and must be visible in the custom report's menu.
            3. All rows must be consistent with the rows from old report.
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_for_base_report_hourly():
    """
    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
        setup:
            1. Navigate to Cloud Intel > Reports > All Schedules.
            2. Click on `Configuration` and select `Add a new Schedule`.
        testSteps:
            1. Create schedule that runs report hourly during the day.
        expectedResults:
            1. Check it was ran successfully.

    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_report_secondary_display_filter_should_be_editable():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1565171

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        title: Report secondary (display) filter should be editable
        setup:
            1. Create report based on container images.
            2. Select some fields for the report.
            3. Go to the filter tab and add a primary filter.
            4. Add secondary filter.
            5. Save the report.
            6. Edit the report.
        testSteps:
            1.Try to edit the secondary filter.
        expectedResults:
            1. Secondary filter must be editable.
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
        setup:
            1. Navigate to Cloud Intel > Reports > All Reports.
        testSteps:
            1. Select any report and create its copy
            2. Locate newly created report in My Company > Custom
            3. Navigate to Import / Export
            4. Select Custom reports
            5. Select newly copied report and select Export
            6. Download the yaml file
            7. Locate exported report in My Company > Custom
            8. Delete exported report
            9. Navigate back to Import / Export
            10. Select Choose file
            11. Locate and select previously downloaded yaml file
            12. Select Upload
            13. Locate import report in My Company > Custom
        expectedResults:
            1.
            2. Verify that canned report was copied under new name
            3.
            4. Verify you"ve been redirected to Import / Export screen
            5. Verify that yaml file download was initiated
            6.
            7.
            8.
            9.
            10. Verify File upload screen was open
            11.
            12. Verify Imported report is now again available for Export
            13. Verify report is present
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_manage_report_menu_accordion_with_users():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1535023

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
        setup:
            1. Create a new report called report01
            2. Create a new user under EvmGroup-super_administrator called
            testuser
            3. "Edit Report Menus" and add the report01 under EvmGroup-
            super_administrator"s Provisioning -> Activities
            4. Login using testuser and navigate to Reports
        testSteps:
            1. Check if the report01 is present under Provisioning -> Activities
        expectedResults:
            1. The report01 must be present under Provisioning -> Activities
    """
    pass



@pytest.mark.manual
@test_requirements.report
def test_report_menus_moving_reports():
    """
    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: low
        initialEstimate: 1/12h
        setup:
            1. Navigate to  Cloud Intel -> Reports -> Edit reports menuSelect EvmGroup
                Administrator -> Configuration Management -> Virtual Machines
            2. Select Virtual Machines folder
        testSteps:
            1. Select 5 Reports and move them to the left.
            2. Reset it.
            3. Select all reports and move them to the left
        expectedResults:
            1. All 5 reports should be moved.
            2. All settings must be reset.
            3. All reports should be moved.

    """
    pass
