import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(1),
    test_requirements.c_and_u,
    pytest.mark.provider(
        [VMwareProvider, RHEVMProvider, EC2Provider, OpenStackProvider, AzureProvider],
        required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')], scope="module")
]


@pytest.mark.tier(1)
@pytest.mark.provider([VMwareProvider], scope="module")
@pytest.mark.parametrize("candu_db_restore", ["utilization_db.backup"], ids=["db"], indirect=True)
def test_utilization_trends(temp_appliance_extended_db, candu_db_restore, request,
        entity_init):
    """
    Test to automate the testing of Overview -> Utilization tab

    Polarion:
        assignee: gtalreja
        casecomponent: Optimize
        initialEstimate: 1/4h
        testSteps:
            1. Enable C&U
            2. Wait until data will be collected
            3. Go to Optimize/Utilization
        expectedResults:
            1.
            2.
            3. Verify that all graphs shows correctly
    """
    with temp_appliance_extended_db:
        view = navigate_to(entity_init, "UtilTrendSummary")

        assert view.summary.chart.is_displayed
        assert view.details.cpu_chart.is_displayed
        assert view.details.memory_chart.is_displayed
        if entity_init == "regions":
            assert view.details.disk_chart.is_displayed
            assert view.report.disk_table.is_displayed
        assert view.report.cpu_table.is_displayed
        assert view.report.memory_table.is_displayed
