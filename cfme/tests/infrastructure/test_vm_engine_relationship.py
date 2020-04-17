import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import InfraVm
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.provider(classes=[InfraProvider], selector=ONE_PER_TYPE),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.rhev,
    test_requirements.general_ui
]

'''
@pytest.fixture
def new_vm(provider, appliance):
    """Get a random vm to mark relationship"""
    view = navigate_to(provider, 'ProviderVms')
    all_names = view.entities.all_entity_names
    try:
        return appliance.collections.infra_vms.instantiate(name=all_names[0], provider=provider)
    except IndexError:
        pytest.skip(f"No VMs found on provider {provider.name}")
'''

@pytest.mark.meta(automates=[1534400])
def test_edit_management_relationship(appliance, create_vm):
    """
    check that Edit Management Relationship works for the VM

    Bugzilla:
        1534400

    Polarion:
        assignee: jhenner
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/6h
    """
    vm_relationship = InfraVm.CfmeRelationship(create_vm)

    for i in range(2):  # do it 2 times and leave the vm w/o relationship
        # set relationship
        vm_relationship.set_relationship(appliance.server.name, appliance.server.sid)
        # unset relationship
        vm_relationship.remove_relationship()
