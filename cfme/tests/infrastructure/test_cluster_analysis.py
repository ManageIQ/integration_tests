# -*- coding: utf-8 -*-

# from cfme.configure.tasks import is_cluster_analysis_finished
from cfme import test_requirements
from cfme.infrastructure import cluster
from cfme.fixtures import pytest_selenium as sel
from utils import testgen
from utils.wait import wait_for

pytestmark = [test_requirements.smartstate]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)

    argnames.append('remove_test')
    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if 'remove_test' not in args['provider'].data:
            # No provisioning data available
            continue

        new_idlist.append(idlist[i])
        argvalues[i].append(args['provider'].data['remove_test'])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def test_run_cluster_analysis(request, setup_provider, provider, remove_test, soft_assert):
    """Tests smarthost analysis

    Metadata:
        test_flag: cluster_analysis
    """
    cluster_name = remove_test['cluster']
    test_cluster = cluster.Cluster(name=cluster_name, provider=provider)
    wait_for(lambda: test_cluster.exists, delay=10, num_sec=120, fail_func=sel.refresh)

    # Initiate analysis
    test_cluster.run_smartstate_analysis()

    # wait_for(lambda: is_cluster_analysis_finished(test_cluster.name),
    # delay=15, timeout="10m", fail_func=lambda: toolbar.select('Reload'))
    # BZ 1216198
    # When SmartState analysis is performed on a cluster,the task is not listed under
    # Configure->Tasks->My other UI tasks

    # TODO:
    # Temporary adding wait_for so data get populated until this BZ 1216198 is resolved
    c_cluster, _ = wait_for(
        lambda: test_cluster.get_detail('Relationships', 'Drift History'),
        delay=20,
        timeout='5m',
        fail_func=sel.refresh,
        fail_condition='None')
    soft_assert(c_cluster != '0', 'No drift history change found')
