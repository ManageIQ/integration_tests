"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.ignore_stream('upstream'),
    pytest.mark.manual,
    test_requirements.chargeback
]


@pytest.mark.tier(2)
def test_validate_chargeback_cost_tiered_rate_fixedvariable_network_cost():
    """
    Validate network I/O used cost  for a tiered rate with fixed and
    variable components

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
def test_validate_chargeback_cost_resource_allocation_cpu_allocated():
    """
    Validate CPU allocated cost in a Chargeback report based on resource
    allocation. C&U data is not considered for these reports.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
def test_validate_chargeback_cost_tiered_rate_fixedvariable_cpu_cost():
    """
    Validate CPU usage cost for a tiered rate with fixed and variable
    components

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
def test_validate_chargeback_cost_resource_allocation_storage_allocated():
    """
    Validate storage allocated cost in a Chargeback report based on
    resource allocation. C&U data is not considered for these reports.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
def test_validate_chargeback_cost_tiered_rate_fixedvariable_disk_cost():
    """
    Validate disk I/O used cost for a tiered rate with fixed and variable
    components

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
def test_validate_chargeback_cost_resource_allocation_memory_allocated():
    """
    Validate memory allocated cost in a Chargeback report based on
    resource allocation. C&U data is not considered for these reports.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
def test_validate_chargeback_cost_tiered_rate_fixedvariable_memory_cost():
    """
    Validate memory usage cost  for a tiered rate with fixed and variable
    components

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
def test_chargeback_report_weekly():
    """
    Verify that 1)weekly chargeback reports can be generated and 2)that
    the report contains relevant data for the relevant period.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_weekly_usage_memory():
    """
    Validate cost for memory usage for a VM in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_weekly_allocation_storage():
    """
    Validate cost for VM storage allocation in a weekly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_weekly_usage_disk():
    """
    Validate cost for disk io for a VM in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_weekly_usage_storage():
    """
    Validate cost for storage usage for a VM in a weekly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_weekly_usage_cpu():
    """
    Validate cost for CPU usage for a VM in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_weekly_allocation_memory():
    """
    Validate cost for VM memory allocation in a weekly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_weekly_usage_network():
    """
    Validate cost for network io for a VM  in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_weekly_allocation_cpu():
    """
    Validate cost for VM CPU allocation in a weekly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_saved_chargeback_report():
    """
    Verify that saved Chargeback reports are saved in the "Saved
    Chargeback Reports" folder on the Cloud Intelligence->Chargeback->
    Report page.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(3)
def test_chargeback_report_compute_provider():
    """
    Assign compute rates to provider;Generate chargeback report and verify
    that rates are applied to selected providers only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(3)
def test_chargeback_report_storage_tenants():
    """
    Assign storage rates to tenants;Generate chargeback report and verify
    that rates are applied to the tenant.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(3)
def test_chargeback_report_compute_tenants():
    """
    Assign compute rates to tenants;Generate chargeback report and verify
    that rates are applied to the tenant.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
def test_chargeback_report_storage_tagged_datastore():
    """
    Assign storage rates to tagged datastore;Generate chargeback report
    and verify that rates are applied to selected datastores only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(2)
def test_chargeback_report_storage_enterprise():
    """
    Assign storage rates to Enterprise;Generate chargeback report and
    verify that rates are applied to Enterprise

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(2)
def test_chargeback_report_compute_cluster():
    """
    Assign compute rates to cluster;Generate chargeback report and verify
    that rates are applied to selected clusters only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(2)
def test_chargeback_report_compute_enterprise():
    """
    Assign compute rates to Enterprise;Generate chargeback report and
    verify that rates are applied to Enterprise

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(3)
def test_chargeback_report_compute_tagged_vm():
    """
    Assign compute rates to tagged Vms;Generate chargeback report and
    verify that rates are applied to tagged VMs only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(3)
def test_chargeback_report_storage_datastore():
    """
    Assign storage rates to datastore;Generate chargeback report and
    verify that rates are applied to selected datastores only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


def test_consistent_capitalization_of_cpu_when_creating_compute_chargeback_rate():
    """
    Consistent capitalization of "CPU":
    1.) When adding a Compute Chargeback Rate, the "CPU" group should not
    change to "Cpu" when you click the "Add" button to add a second
    tier/row.
    2.) The "CPU Cores" group should not display as "Cpu Cores".

    Polarion:
        assignee: tpapaioa
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/15h
    """
    pass


def test_validate_cost_monthly_usage_storage():
    """
    Validate cost for storage usage for a VM in a monthly chargeback
    report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_monthly_usage_disk():
    """
    Validate cost for disk io for a VM in a monthly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_monthly_allocation_cpu():
    """
    Validate cost for VM cpu allocation in a monthly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_monthly_allocation_storage():
    """
    Validate cost for VM storage allocation in a monthly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_monthly_usage_cpu():
    """
    Validate cost for CPU usage for a VM in a monthly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_monthly_allocation_memory():
    """
    Validate cost for VM memory allocation in a monthly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_monthly_usage_memory():
    """
    Validate cost for memory usage for a VM in a monthly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


def test_validate_cost_monthly_usage_network():
    """
    Validate cost for network io for a VM in a monthly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_chargeback_report_filter_owner():
    """
    Verify that chargeback reports can be generated by filtering on
    owners.Make sure to include the "owner" column in the report.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(3)
def test_chargeback_report_filter_tag():
    """
    Verify that chargeback reports can be generated by filtering on tags

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


def test_chargeback_report_monthly():
    """
    Verify that 1)monthly chargeback reports can be generated and 2)that
    the report contains relevant data for the relevant period.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_chargeback_preview():
    """
    Verify that Chargeback Preview is generated for VMs

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


def test_validate_chargeback_cost_resource_average_cpu():
    """
    Validate cost for allocated CPU with "Average" method for allocated
    metrics.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


def test_validate_chargeback_cost_resource_average_memory():
    """
    Validate cost for allocated memory with "Average" method for allocated
    metrics

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


def test_validate_chargeback_cost_resource_maximum_cpu():
    """
    Validate cost for allocated CPU with "Maximum" method for allocated
    metrics
    1))Let VM run for a few hours(3- 24 hours)
    2)Sometime during that interval(3-24 hours),reconfigure VM to have
    different resources from when it was created(add/remove
    vCPU,memory,disk)
    3)Validate that chargeback costs are appropriate for vCPU allocated
    when method for allocated metrics is "Maximum".
    Also, see RHCF3-34343, RHCF3-34344, RHCF3-34345, RHCF3-34346,
    RHCF3-34347 .

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


def test_validate_chargeback_cost_resource_maximum_storage():
    """
    Validate cost for allocated storage with "Maximum" method for
    allocated metrics

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


def test_validate_chargeback_cost_resource_average_stoarge():
    """
    Validate cost for allocated storage with "Average" method for
    allocated metrics

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


def test_validate_chargeback_cost_resource_maximum_memory():
    """
    Validate cost for allocated memory with "Maximum" method for allocated
    metrics

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass
