# -*- coding: utf-8 -*-

from cfme.configure import tasks
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import datastore, host
from cfme.web_ui import flash, tabstrip as tabs, toolbar as tb
from utils import conf, testgen
from utils.providers import setup_provider
from utils.wait import wait_for
import pytest

DATASTORE_TYPES = ('vmfs', 'nfs', 'iscsi')

# rhevm not supported
PROVIDER_TYPES = ('virtualcenter',)

# Rows to check in the datastore detail Content infoblock; after smartstate analysis
CONTENT_ROWS_TO_CHECK = (
    'All Files',
    'VM Provisioned Disk Files',
    'VM Snapshot Files',
    'VM Memory Files',
    'Other VM Files',
    'Non-VM Files'
)


def pytest_generate_tests(metafunc):
    p_argn, p_argv, p_ids = testgen.provider_by_type(metafunc, PROVIDER_TYPES, 'datastores')
    argnames = ['provider_key', 'datastore_type', 'datastore_name']
    argvalues = []
    idlist = []
    for argv in p_argv:
        prov_datastores, prov_key = argv[0], argv[1]
        if not prov_datastores:
            continue
        for test_datastore in prov_datastores:
            if not test_datastore.get('test_fleece', False):
                continue
            assert test_datastore.get('type', None) in DATASTORE_TYPES,\
                'datastore type must be set to [{}] for smartstate analysis tests'\
                .format('|'.join(DATASTORE_TYPES))

            argvalues.append([prov_key, test_datastore['type'], test_datastore['name']])
            test_id = '{}-{}-{}'.format(prov_key, test_datastore['type'], test_datastore['name'])
            idlist.append(test_id)

    metafunc.parametrize(argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture()
def provider_init(provider_key):
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data['management_systems'][provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


# TODO add support for events
@pytest.mark.bugzilla(
    1091033,
    unskip={
        1091033: lambda datastore_type: datastore_type != 'iscsi'
    }
)
def test_run_datastore_analysis(request, provider_init, provider_key,
                                datastore_type, datastore_name):
    """ Run host SmartState analysis
    """
    test_datastore = datastore.Datastore(datastore_name, provider_key)

    # Check if there is a host with valid credentials
    host_qis = test_datastore.get_hosts()
    assert len(host_qis) != 0, "No hosts attached to this datastore found"
    for host_qi in host_qis:
        if host_qi.creds == 'checkmark':
            break
    else:
        # If not, get credentials for one of the present hosts
        found_host = False
        for host_qi in host_qis:
            host_data = get_host_data_by_name(provider_key, host_qi._name)
            if host_data is None:
                continue

            found_host = True
            test_host = host.Host(name=host_qi._name)

            # Add them to the host
            wait_for(lambda: test_host.exists, delay=10, num_sec=120, fail_func=sel.refresh)
            if not test_host.has_valid_credentials:
                test_host.update(
                    updates={
                        'credentials': host.get_credentials_from_config(host_data['credentials'])}
                )
                wait_for(
                    lambda: test_host.has_valid_credentials,
                    delay=10,
                    num_sec=120,
                    fail_func=sel.refresh
                )

                # And remove them again when the test is finished
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
            break

        assert found_host,\
            "No credentials found for any of the hosts attached to datastore {}"\
            .format(datastore_name)

    # TODO add support for events
    # register_event(
    #     None,
    #     "datastore",
    #     datastore_name,
    #     ["datastore_analysis_request_req", "datastore_analysis_complete_req"]
    # )

    # Initiate analysis
    sel.force_navigate('infrastructure_datastore', context={
        'datastore': test_datastore,
        'provider': test_datastore.provider
    })
    tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_contain('"{}": scan successfully initiated'.format(datastore_name))

    # Wait for the task to finish
    def is_datastore_analysis_finished():
        """ Check if analysis is finished - if not, reload page
        """
        if not sel.is_displayed(tasks.tasks_table) or not tabs.is_tab_selected('All Other Tasks'):
            sel.force_navigate('tasks_all_other')
        host_analysis_finished = tasks.tasks_table.find_row_by_cells({
            'task_name': "SmartState Analysis for [{}]".format(datastore_name),
            'state': 'Finished'
        })
        return host_analysis_finished is not None

    wait_for(
        is_datastore_analysis_finished,
        delay=10,
        num_sec=300,
        fail_func=lambda: tb.select('Reload')
    )

    # Delete the task
    tasks.tasks_table.select_row_by_cells({
        'task_name': "SmartState Analysis for [{}]".format(datastore_name),
        'state': 'Finished'
    })
    tb.select('Delete Tasks', 'Delete', invokes_alert=True)
    sel.handle_alert()

    # Check results of the analysis and the datastore type
    assert test_datastore.get_detail('Properties', 'Datastore Type') == datastore_type.upper(),\
        'Datastore type does not match the type defined in yaml'
    for row_name in CONTENT_ROWS_TO_CHECK:
        assert test_datastore.get_detail('Content', row_name) != '0',\
            '{} in Content infoblock should not be 0'.format(row_name)
