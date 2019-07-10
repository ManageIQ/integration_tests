import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.report,
    pytest.mark.tier(3)
]

PROPERTY_MAPPING = {
    "cpu": "Allocated Virtual CPUs",
    "memory": "Allocated Memory in GB",
    "storage": "Allocated Storage in GB",
    "template": "Allocated Number of Templates",
    "vm": "Allocated Number of Virtual Machines",
}


@pytest.fixture(scope="function")
def set_and_get_tenant_quota(appliance):
    root_tenant = appliance.collections.tenants.get_root_tenant()

    view = navigate_to(root_tenant, "ManageQuotas")
    reset_data = view.form.read()

    tenant_quota_data = {
        "cpu_cb": True,
        "cpu": "10",
        "memory_cb": True,
        "memory": "50.0",
        "storage_cb": True,
        "storage": "150.0",
        "template_cb": True,
        "template": "5",
        "vm_cb": True,
        "vm": "15",
    }

    root_tenant.set_quota(**tenant_quota_data)

    data = dict()
    for key, value in PROPERTY_MAPPING.items():
        suffix = "GB" if "GB" in value else "Count"
        data[value] = "{data_value} {suffix}".format(
            data_value=tenant_quota_data[key], suffix=suffix
        )

    yield data

    root_tenant.set_quota(**reset_data)


@pytest.fixture(scope="function")
def tenant_report(appliance):
    tenant_report = appliance.collections.reports.instantiate(
        type="Tenants", subtype="Tenant Quotas", menu_name="Tenant Quotas"
    ).queue(wait_for_finish=True)

    yield tenant_report

    tenant_report.delete()


def test_queue_tenant_quota_reports(set_and_get_tenant_quota, tenant_report):
    """This test case sets the tenant quota, generates a 'Tenant Quota' report
        and compares both the data.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/10h
        tags: report
        setup:
            1. Set tenant quota
            2. Create the report
        testSteps:
            1. Compare the 'total quota' data in the reports and the quota that was set initially.
        expectedResults:
            1. Both the data must be same.
    """
    report_data = dict()
    for row in tenant_report.data.rows:
        if row["Quota Name"] in list(PROPERTY_MAPPING.values()):
            report_data[row["Quota Name"]] = row["Total Quota"]
    assert report_data == set_and_get_tenant_quota


def test_report_fullscreen_enabled(request, tenant_report, set_and_get_tenant_quota, soft_assert):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/12h
        tags: report
        setup:
            1. Navigate to Cloud > Intel > Reports > All Reports
        testSteps:
            1. Select a report that would generate an empty report on queueing.
            Queue it, navigate to it's `Details` page, click on Configuration and
            check the `Show Fullscreen Report` option.
            2. Select a report that would generate a populated report on queueing.
            Queue it, navigate to it's `Details` page, click on Configuration and
            check the `Show Fullscreen Report` option.
        expectedResults:
            1. `Show Fullscreen Report` option is Disabled.
            2. `Show Fullscreen Report` option is Enabled.
    """
    empty_report = tenant_report
    view = navigate_to(empty_report, "Details", use_resetter=False)
    assert not view.configuration.item_enabled("Show full screen Report")

    non_empty_report = tenant_report.parent.parent.queue(wait_for_finish=True)
    request.addfinalizer(non_empty_report.delete)

    view = navigate_to(non_empty_report, "Details", use_resetter=False)
    assert view.configuration.item_enabled("Show full screen Report")
