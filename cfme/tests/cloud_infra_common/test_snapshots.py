import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    pytest.mark.manual,
    pytest.mark.provider([VMwareProvider, RHEVMProvider, OpenStackProvider], scope='module'),
]


@pytest.mark.meta(coverage=[1708758])
def test_snapshot_image_copies_system_info():
    """
    Verify that system info is copied to image during making a snapshot of vm

    Polarion:
        assignee: prichard
        casecomponent: Appliance
        initialEstimate: 1/2h
        tags: smartstate, providers
        testSteps:
            1. Add a Provider.
            2. provision vm and make sure it has os_version and os_distro set
            3. make an image of it by creating snapshot
        expectedResults:
            1.
            2.
            3. vm/system info is present in the image
    """
