# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import pytest

from cfme.configure import tasks
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import host as host_obj
from cfme.web_ui import DriftGrid, toolbar as tb, tabstrip as tabs
from utils import error, testgen
from utils.wait import wait_for

pytestmark = [pytest.mark.tier(3)]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, required_fields=['hosts'])
    argnames += ['host']

    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        for test_host in args['provider'].data['hosts']:
            if not test_host.get('test_fleece', False):
                continue

            argvs = argvalues[i][:]
            new_argvalues.append(argvs + [test_host])
            test_id = '{}-{}'.format(args['provider'].key, test_host['type'])
            new_idlist.append(test_id)
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.mark.meta(blockers=[1242655])
def test_host_drift_analysis(request, setup_provider, provider, host, soft_assert):
    """Tests host drift analysis

    Metadata:
        test_flag: host_drift_analysis
    """
    test_host = host_obj.Host(name=host['name'])

    wait_for(lambda: test_host.exists, delay=10, num_sec=120, fail_func=sel.refresh,
             message="hosts_exists")

    # get drift history num
    drift_num_orig = int(test_host.get_detail('Relationships', 'Drift History'))

    # add credentials to host + finalizer to remove them
    if not test_host.has_valid_credentials:
        test_host.update(
            updates={'credentials': host_obj.get_credentials_from_config(host['credentials'])},
            validate_credentials=True
        )

        @request.addfinalizer
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

    # initiate 1st analysis
    test_host.run_smartstate_analysis()

    # Wait for the task to finish
    def is_host_analysis_finished():
        """ Check if analysis is finished - if not, reload page
        """
        if not sel.is_displayed(tasks.tasks_table) or not tabs.is_tab_selected('All Other Tasks'):
            sel.force_navigate('tasks_all_other')
        host_analysis_finished = tasks.tasks_table.find_row_by_cells({
            'task_name': "SmartState Analysis for '{}'".format(test_host.name),
            'state': 'Finished'
        })
        if host_analysis_finished:
            # Delete the task
            tasks.tasks_table.select_row_by_cells({
                'task_name': "SmartState Analysis for '{}'".format(test_host.name),
                'state': 'Finished'
            })
            tb.select('Delete Tasks', 'Delete', invokes_alert=True)
            sel.handle_alert()
        return host_analysis_finished is not None

    wait_for(is_host_analysis_finished,
             delay=15, timeout="8m", fail_func=lambda: tb.select('Reload'))

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

    # Wait for the task to finish
    wait_for(is_host_analysis_finished,
             delay=15, timeout="8m", fail_func=lambda: tb.select('Reload'))

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
