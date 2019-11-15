"""Manual tests"""
import pytest

from cfme import test_requirements
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI


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
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("5.10")
def test_reports_timezone():
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/10h
        startsin: 5.11
        setup:
            1. Navigate to My Settings and change the timezone.
            2. Create a report with the date created field
            3. Run report
        testSteps:
            1. Check the timezone in the report.
        expectedResults:
            1. Timezone must be same as set in My Settings.

    Bugzilla:
        1599849
    """
    pass


@pytest.mark.manual
@test_requirements.report
@test_requirements.multi_region
@pytest.mark.tier(2)
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.parametrize('report', ['new-report', 'existing-report'])
def test_reports_in_global_region(context, report):
    """
    This test case tests report creation and rendering from global region
    based on data from remote regions.

    Polarion:
        assignee: izapolsk
        casecomponent: Reporting
        caseimportance: critical
        initialEstimate: 1/2h
        testSteps:
            1. Set up Multi-Region deployment with 2 remote region appliances
            2. Add provider to each remote appliance
            3. Create and render report in global region. report should use data from both providers
            4. Use one of existing reports using data from added providers
        expectedResults:
            1.
            2.
            3. Report should be created and rendered successfully and show expected data.
            4. Report should be rendered successfully and show expected data.

    """
    pass


@test_requirements.report
@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1743579])
def test_created_on_time_report_field():
    """
    Bugzilla:
        1743579

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/2h
        setup:
            1. Add a provider and provision a VM
        testSteps:
            1. Create a report based on 'VMs and Instances' with [Created on Time, Name] field.
        expectedResults:
            1. `Created on Time` field column must not be empty for the recently created VM.
    """
    pass


@pytest.mark.ignore_stream("5.10")
@test_requirements.report
@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1714197])
def test_optimization_reports():
    """
    Bugzilla:
        1714197

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/2h
        startsin: 5.11
        testSteps:
            1. Navigate to Overview > Optimization.
            2. Queue all the 7 parametrized reports and check if it exists.
        expectedResults:
            1.
            2. Reports must exist.
    """
    pass


@pytest.mark.ignore_stream("5.10")
@test_requirements.report
@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1743651])
def test_reports_timelines_tab():
    """
    Bugzilla:
        1743651

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.11
        testSteps:
            1. Copy a report based on timeline and check if the Timelines tab is visible.
        expectedResults:
            1. Timelines tab must not be visible.
    """
    pass
