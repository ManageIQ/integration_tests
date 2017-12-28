# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.smartstate,
    pytest.mark.provider([InfraProvider], required_fields=[['remove_test', 'cluster']],
                         scope="module")
]


def test_run_cluster_analysis(setup_provider, provider, appliance):
    """Tests smarthost analysis

    Metadata:
        test_flag: cluster_analysis
    """
    cluster_name = provider.data.remove_test.cluster
    cluster_col = appliance.collections.clusters
    test_cluster = cluster_col.instantiate(name=cluster_name, provider=provider)
    test_cluster.wait_for_exists()

    # Initiate analysis
    # Todo add check for task completion, for cluster task is not available for now
    test_cluster.run_smartstate_analysis()

    cluster_view = navigate_to(test_cluster, 'Details')
    drift_num = wait_for(lambda: cluster_view.entities.relationships.get_text_of('Drift History'),
                         delay=20, timeout='5m', fail_func=appliance.server.browser.refresh,
                         fail_condition='None')
    assert drift_num != '0', 'No drift history change found'
