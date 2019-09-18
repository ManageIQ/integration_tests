# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.long_running,
]


@pytest.mark.manual
@pytest.mark.tier(2)
@test_requirements.multi_region
@test_requirements.service
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.parametrize('catalog_location', ['global', 'remote'])
@pytest.mark.parametrize('item_type', ['AMAZON', 'ANSIBLE', 'TOWER', 'AZURE', 'GENERIC',
                                       'OPENSTACK', 'ORCHESTRATION', 'RHV', 'SCVMM', 'VMWARE',
                                       'BUNDLE'])
@pytest.mark.uncollectif(lambda catalog_location: catalog_location == 'global',
                         reason="isn't supported yet")
def test_service_provision_retire_from_global_region(item_type, catalog_location, context):
    """
    Polarion:
        assignee: izapolsk
        caseimportance: high
        casecomponent: Services
        initialEstimate: 1/3h
    """
    pass
