import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.smartstate,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE),
]


def test_run_cluster_analysis(appliance, provider):
    """Tests smarthost analysis

    Metadata:
        test_flag: cluster_analysis

    Polarion:
        assignee: nansari
        casecomponent: SmartState
        initialEstimate: 1/3h
    """
    cluster_coll = appliance.collections.clusters.filter({'provider': provider})
    test_cluster = cluster_coll.all()[0]
    test_cluster.wait_for_exists()

    # Initiate analysis
    # Todo add check for task completion, for cluster task is not available for now
    test_cluster.run_smartstate_analysis()

    cluster_view = navigate_to(test_cluster, 'Details')
    drift_num = wait_for(lambda: cluster_view.entities.relationships.get_text_of('Drift History'),
                         delay=20, timeout='5m', fail_func=appliance.server.browser.refresh,
                         fail_condition='None')
    assert drift_num != '0', 'No drift history change found'
