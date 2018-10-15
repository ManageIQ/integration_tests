import pytest


property_mapping = {
    "cpu": "Allocated Virtual CPUs",
    "memory": "Allocated Memory in GB",
    "storage": "Allocated Storage in GB",
    "template": "Allocated Number of Templates",
    "vm": "Allocated Number of Virtual Machines",
}


@pytest.fixture(scope="module")
def set_and_get_tenant_quota(appliance):
    root_tenant = appliance.collections.tenants.get_root_tenant()
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
    for key, value in property_mapping.items():
        suffix = "GB" if "GB" in value else "Count"
        data[value] = '{0} {1}'.format(tenant_quota_data[key], suffix)

    yield data

    reset_data = {
        "cpu_cb": False,
        "memory_cb": False,
        "storage_cb": False,
        "template_cb": False,
        "vm_cb": False,
    }
    root_tenant.set_quota(**reset_data)


def test_queue_tenant_quota_reports(appliance, request, set_and_get_tenant_quota):
    """
        This test case sets the tenant quota, generates a 'Tenant Quota' report
        and compares both the data.
    """
    tenant_report = appliance.collections.reports.instantiate(
        type="Tenants", subtype="Tenant Quotas", menu_name="Tenant Quotas"
    ).queue(wait_for_finish=True)
    request.addfinalizer(tenant_report.delete)

    report_data = dict()
    for row in tenant_report.data.rows:
        if row["Quota Name"] in property_mapping.values():
            report_data[row["Quota Name"]] = row["Total Quota"]
    assert report_data == set_and_get_tenant_quota
