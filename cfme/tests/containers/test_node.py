import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.exceptions import NodeNotFound
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.containers
]


TEST_DEST = ('All', 'Details')


@pytest.mark.tier(3)
@pytest.mark.provider([ContainersProvider])
def test_nodes_navigate(soft_assert, appliance):

    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    for dest in TEST_DEST:

        if dest == 'All':
            test_item = appliance.collections.container_nodes
        elif dest == 'Details':
            try:
                test_item = appliance.collections.container_nodes.all()[0]
            except IndexError:
                pytest.skip('No Nodes available, skipping test')

        try:
            view = navigate_to(test_item, dest)
        except NodeNotFound:
            soft_assert(False, 'Could not navigate to Node "{}" .'.format(dest))
        else:
            # Navigation successful, page is displayed
            assert view.is_displayed
