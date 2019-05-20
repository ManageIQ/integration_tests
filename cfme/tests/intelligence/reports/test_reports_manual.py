# -*- coding: utf-8 -*-
"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_import_invalid_file():
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
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
    Bugzilla:
        1521167

    Polarion:
        assignee: pvala
        casecomponent: Reporting
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
        casecomponent: Reporting
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
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/4h
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
def test_after_setting_certain_types_of_filters_filter_tab_should_be_accessible_and_editable():
    """
    Bugzilla:
        1519809

    Polarion:
        assignee: pvala
        casecomponent: Reporting
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
def test_date_should_be_change_in_editing_reports_scheduled():
    """
    Bugzilla:
        1446052

    Polarion:
        assignee: pvala
        casecomponent: Reporting
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
def test_report_secondary_display_filter_should_be_editable():
    """
    Bugzilla:
        1565171

    Polarion:
        assignee: pvala
        casecomponent: Reporting
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
        casecomponent: Reporting
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
    Bugzilla:
        1535023

    Polarion:
        assignee: pvala
        casecomponent: Reporting
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
@pytest.mark.tier(1)
def test_report_menus_moving_reports():
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/12h
        setup:
            1. Navigate to  Cloud Intel -> Reports -> Edit reports menu
            2. Select EvmGroupAdministrator -> Configuration Management -> Virtual Machines
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


@pytest.mark.manual
@test_requirements.report
@test_requirements.timelines
@pytest.mark.tier(2)
@pytest.mark.parametrize(
    "report_type", ["hosts", "vm_operation", "policy_events", "custom"]
)
def test_custom_reports_with_timelines(report_type):
    """
    Cloud Intel->Reports allows to copy existing reports with timelines or
    create new ones from scratch.
    Such custom reports appear in Cloud Intel -> Timelines after creation.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/3h
        setup:
            1. Navigate to Cloud Intel > Reports > All Reports.
            2. In the `All Reports` accordion, trace the report based on report_type.
                and copy the report or create a new report if the report_type is `custom`.
            3. Navigate to Cloud Intel > Timelines.
        testSteps:
            1. Check the Timelines tree.
        expectedResults:
            1. The copied/new report must appear under in the tree.
                under [My Company (All Groups), Custom].
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_sent_text_custom_report_with_long_condition():
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/3h
        setup:
            1. Create a report containing 1 or 2 columns
                and add a report filter with a long condition.(Refer BZ for more detail)
            2. Create a schedule for the report and check send_txt.
        testSteps:
            1. Queue the schedule and monitor evm log.
        expectedResults:
            1. There should be no error in the log and report must be sent successfully.

    Bugzilla:
        1677839
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_vm_volume_free_space_less_than_20_percent():
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/3h
        setup:
            1. Go to Cloud Intel -> Reports -> All Reports
        testSteps:
            1. Queue the report
                [Configuration Management, Virtual Machines, VMs with Volume Free Space <= 20%]
        expectedResults:
            1. It should report only those VMs which has volume free space less than
                or equal to 20%.

    Bugzilla:
        1686281
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(0)
@pytest.mark.ignore_stream("5.10")
def test_reports_filter_content():
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/3h
        startsin: 5.11
        setup:
            1. Go to Cloud Intel -> Reports -> All Reports
            2. Select a report and queue it, make sure it's not empty.
        testSteps:
            1. Add a filter.
            2. Traverse through all the rows and check if the content is filtered.
        expectedResults:
            1.
            2. Content must be filtered.

    Bugzilla:
        1678150
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(0)
@pytest.mark.ignore_stream("5.10")
def test_reports_sort_column():
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/3h
        startsin: 5.11
        setup:
            1. Go to Cloud Intel -> Reports -> All Reports
            2. Select a report and queue it, make sure it's not empty.
            3. Note the order of content of a targetted column.
        testSteps:
            1. Sort the targetted column on the basis of some property.
            2. Traverse through all the rows, note the order of content of the targetted column.
            3. Sort the first order and compare it with the second order.
        expectedResults:
            1.
            2.
            3. Both the orders must be same.

    Bugzilla:
        1678150
    """
    pass
