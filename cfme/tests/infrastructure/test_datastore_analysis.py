# -*- coding: utf-8 -*-

from cfme.configure import tasks
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import datastore, host
from cfme.web_ui import flash, tabstrip as tabs, toolbar as tb, Quadicon, InfoBlock
from utils import conf, testgen, version
from utils.blockers import BZ
from utils.wait import wait_for
import pytest

DATASTORE_TYPES = ('vmfs', 'nfs', 'iscsi')
# rhevm supported in 5.3+
PROVIDER_TYPES = {
    version.LOWEST: ('virtualcenter',),
    '5.3': ('virtualcenter', 'rhevm')
}

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
    verpicked_prov_types = version.pick(PROVIDER_TYPES)

    new_idlist = []
    new_argvalues = []

    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, verpicked_prov_types, 'datastores')
    argnames += ['datastore_type', 'datastore_name']

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if not args['datastores']:
            continue
        for ds in args['datastores']:
            if not ds.get('test_fleece', False):
                continue
            assert ds.get('type', None) in DATASTORE_TYPES,\
                'datastore type must be set to [{}] for smartstate analysis tests'\
                .format('|'.join(DATASTORE_TYPES))
            argvs = argvalues[i][:]
            argvs.pop(argnames.index('datastores'))
            new_argvalues.append(argvs + [ds['type'], ds['name']])
            test_id = '{}-{}-{}'.format(args['provider'].key, ds['type'], ds['name'])
            new_idlist.append(test_id)
    argnames.remove('datastores')
    metafunc.parametrize(argnames, new_argvalues, ids=new_idlist, scope="module")


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


# TODO add support for events
@pytest.mark.meta(
    blockers=[
        BZ(1091033, unblock=lambda datastore_type: datastore_type != 'iscsi'),
        BZ(1180467, unblock=lambda provider: provider.type != 'rhevm'),
    ]
)
def test_run_datastore_analysis(request, setup_provider, provider, datastore_type, datastore_name,
                                soft_assert):
    """Tests smarthost analysis

    Metadata:
        test_flag: datastore_analysis
    """
    test_datastore = datastore.Datastore(datastore_name, provider.key)

    # Check if there is a host with valid credentials
    host_names = test_datastore.get_hosts()
    assert len(host_names) != 0, "No hosts attached to this datastore found"
    for host_name in host_names:
        host_qi = Quadicon(host_name, 'host')
        if host_qi.creds == 'checkmark':
            break
    else:
        # If not, get credentials for one of the present hosts
        found_host = False
        for host_name in host_names:
            host_data = get_host_data_by_name(provider.key, host_name)
            if host_data is None:
                continue

            found_host = True
            test_host = host.Host(name=host_name)

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

    c_datastore = test_datastore.get_detail('Properties', 'Datastore Type')
    # Check results of the analysis and the datastore type
    soft_assert(c_datastore == datastore_type.upper(),
                'Datastore type does not match the type defined in yaml:' +
                'expected "{}" but was "{}"'.format(datastore_type.upper(), c_datastore))
    for row_name in CONTENT_ROWS_TO_CHECK:
        value = InfoBlock('Content', row_name).text
        soft_assert(value != '0',
                    'Expected value for {} to be non-empty'.format(row_name))
