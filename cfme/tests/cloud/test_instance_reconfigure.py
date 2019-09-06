import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.long_running,
]


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.provider([OpenStackProvider], required_fields=['templates'],
                      selector=ONE_PER_TYPE, override=True)
@test_requirements.multi_region
@test_requirements.reconfigure
def test_vm_reconfigure_from_global_region(context):
    """
    reconfigure a VM via CA

    Polarion:
        assignee: izapolsk
        caseimportance: medium
        casecomponent: Infra
        initialEstimate: 1/3h
        testSteps:
            1. Have a VM created in the provider in the Remote region which is
               subscribed to Global.
            2. Reconfigure the VM using the Global appliance.
        expectedResults:
            1.
            2. VM reconfigured, no errors.
    """
    pass
