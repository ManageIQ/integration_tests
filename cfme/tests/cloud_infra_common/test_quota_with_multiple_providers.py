import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_TYPE,
        scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name='source_provider',
        scope="module"
    )
]


@test_requirements.quota
@pytest.mark.tier(2)
def test_show_quota_used_on_tenant_screen(appliance, v2v_provider_setup):
    """Test show quota used on tenant quota screen even when no quotas are set.

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        caseimportance: low
        caseposneg: positive
        casecomponent: Infra
        tags: quota
        testSteps:
            1. Add two infra providers
            2. Navigate to provider's 'Details' page.
            3. Fetch the information of 'number of VMs'.
            4. Navigate to 'Details' page of 'My Company' tenant.
            5. Go to tenant quota table.
            6. Check whether number of VMs are equal to number of VMs in 'in use' column.
    """
    v2v_provider_setup.vmware_provider.refresh_provider_relationships
    v2v_provider_setup.rhv_provider.refresh_provider_relationships
    vm_count = (
        v2v_provider_setup.rhv_provider.num_vm() + v2v_provider_setup.vmware_provider.num_vm()
    )
    root_tenant = appliance.collections.tenants.get_root_tenant()
    view = navigate_to(root_tenant, "Details")
    for row in view.table:
        if row[0].text == "Allocated Number of Virtual Machines":
            num_of_vms = row[2].text
    num_of_vms = int(num_of_vms.split()[0])
    assert vm_count == num_of_vms
