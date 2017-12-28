# -*- coding: utf-8 -*-
import pytest

# from cfme.configure.tasks import is_cluster_analysis_finished
from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.smartstate,
    pytest.mark.provider([InfraProvider], required_fields=['remove_test'], scope="module")
]


def test_run_cluster_analysis(setup_provider, provider, appliance):
    """Tests smarthost analysis

    Metadata:
        test_flag: cluster_analysis
    """
    cluster_name = provider.data['remove_test']['cluster']
    cluster_col = appliance.collections.clusters
    test_cluster = cluster_col.instantiate(name=cluster_name, provider=provider)
    test_cluster.wait_for_exists()

    # Initiate analysis
    test_cluster.run_smartstate_analysis()

    drift_num = wait_for(lambda: test_cluster.get_detail('Relationships', 'Drift History'),
                         delay=20, timeout='5m', fail_func=appliance.browser.reload,
                         fail_condition='None')
    assert drift_num != '0', 'No drift history change found'
