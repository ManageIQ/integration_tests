# -*- coding: utf-8 -*-

import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import host
from cfme.web_ui import DriftGrid, toolbar as tb
from utils import conf, error, testgen
from utils.wait import wait_for


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'hosts')
    argnames += ['host_type', 'host_name']

    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if not args['hosts']:
            continue
        for test_host in args['hosts']:
            if not test_host.get('test_fleece', False):
                continue

            argvs = argvalues[i][:]
            argvs.pop(argnames.index('hosts'))
            new_argvalues.append(argvs + [test_host['type'], test_host['name']])
            test_id = '{}-{}-{}'.format(args['provider'].key, test_host['type'], test_host['name'])
            new_idlist.append(test_id)
    argnames.remove('hosts')
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


@pytest.mark.meta(blockers=[1242655])
def test_host_drift_analysis(request, setup_provider, provider, host_type, host_name, soft_assert):
    """Tests host drift analysis

    Metadata:
        test_flag: host_drift_analysis
    """
    host_data = get_host_data_by_name(provider.key, host_name)
    test_host = host.Host(name=host_name)

    wait_for(lambda: test_host.exists, delay=10, num_sec=120, fail_func=sel.refresh,
             message="hosts_exists")

    # get drift history num
    drift_num_orig = int(test_host.get_detail('Relationships', 'Drift History'))

    # add credentials to host + finalizer to remove them
    if not test_host.has_valid_credentials:
        test_host.update(
            updates={'credentials': host.get_credentials_from_config(host_data['credentials'])}
        )
        wait_for(
            lambda: test_host.has_valid_credentials,
            delay=10,
            num_sec=120,
            fail_func=sel.refresh,
            message="has_valid_credentials"
        )

        def test_host_remove_creds():
            test_host.update(
                updates={
                    'credentials': host.Host.Credential(
                        principal="",
                        secret="",
                        verify_secret=""
                    )
                }
            )
        request.addfinalizer(test_host_remove_creds)

    # initiate 1st analysis
    test_host.run_smartstate_analysis()

    # wait for for drift history num+1
    wait_for(
        lambda: int(test_host.get_detail('Relationships', 'Drift History')) == drift_num_orig + 1,
        delay=20,
        num_sec=120,
        message="Waiting for Drift History count to increase",
        fail_func=sel.refresh
    )

    # add a tag and a finalizer to remove it
    tag = ('Department', 'Accounting')
    test_host.tag(tag, single_value=False)
    request.addfinalizer(lambda: test_host.untag(tag))

    # initiate 2nd analysis
    test_host.run_smartstate_analysis()

    # wait for for drift history num+2
    wait_for(
        lambda: int(test_host.get_detail('Relationships', 'Drift History')) == drift_num_orig + 2,
        delay=20,
        num_sec=120,
        message="Waiting for Drift History count to increase",
        fail_func=sel.refresh
    )

    # check drift difference
    soft_assert(not test_host.equal_drift_results('Department (1)', 'My Company Tags', 0, 1),
        "Drift analysis results are equal when they shouldn't be")

    # Test UI features that modify the drift grid
    d_grid = DriftGrid()

    # Accounting tag should not be displayed, because it was changed to True
    tb.select("Attributes with same values")
    with error.expected(sel.NoSuchElementException):
        d_grid.get_cell('Accounting', 0)

    # Accounting tag should be displayed now
    tb.select("Attributes with different values")
    d_grid.get_cell('Accounting', 0)
