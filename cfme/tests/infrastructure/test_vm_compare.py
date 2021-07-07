import pytest

from cfme.fixtures.provider import setup_or_skip
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import InfraVmCollection
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([InfraProvider],
                         scope='module',
                         selector=ONE_PER_TYPE),
]


@pytest.fixture
def setup_provider_min_vms(request, appliance, provider, min_vms):
    if len(provider.mgmt.list_vms()) < min_vms:
        pytest.skip(f'Number of templates on {provider} does not meet minimum '
                    f'for test parameter {min_vms}, skipping and not setting up provider')
    # Function-scoped fixture to set up a provider
    setup_or_skip(request, provider)


@pytest.mark.provider([InfraProvider], selector=ONE, scope="function")
@pytest.mark.parametrize("min_vms", [2, 4])
@pytest.mark.parametrize("vm_collection", ["provider", "appliance"])
@pytest.mark.meta(blockers=[BZ(1784180, forced_streams=["5.10"])], automates=[1784180])
def test_compare_vms(appliance, setup_provider_min_vms, provider, min_vms, vm_collection):
    """
    Polarion:
        assignee: prichard  ????????
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/6h
    """
    if vm_collection == 'provider':
        provider.collections.vms = InfraVmCollection(provider, filters={'provider': provider})
        t_coll = provider.collections.vms.all()[:min_vms]
        provider.collections.vms.compare_entities_col(provider, entities_list=t_coll)
    elif vm_collection == 'appliance':
        appliance.collections.vms = InfraVmCollection(appliance)
        t_coll = appliance.collections.templates.all()[:min_vms]
        appliance.collections.vms.compare_entities_col(provider, entities_list=t_coll)
