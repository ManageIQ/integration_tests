import pytest

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_TYPE,
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name='second_provider',
    )
]


def test_show_quota_used_on_tenant_screen(request, appliance, v2v_providers):
    """Test show quota used on tenant quota screen even when no quotas are set.

    Steps:
        1. Navigate to provider's 'Details' page.
        2. Fetch the information of 'number of VMs'.
        3. Navigate to 'Details' page of 'My Company' tenant.
        4. Go to tenant quota table.
        5. Check whether number of VMs are equal to number of VMs in 'in use' column.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
    """
    v2v_providers.vmware_provider.refresh_provider_relationships
    v2v_providers.rhv_provider.refresh_provider_relationships
    vm_count = v2v_providers.rhv_provider.num_vm() + v2v_providers.vmware_provider.num_vm()
    root_tenant = appliance.collections.tenants.get_root_tenant()
    view = navigate_to(root_tenant, "Details")
    for row in view.table:
        if row[0].text == "Allocated Number of Virtual Machines":
            num_of_vms = row[2].text
    num_of_vms = int(num_of_vms.split()[0])
    assert vm_count == num_of_vms
