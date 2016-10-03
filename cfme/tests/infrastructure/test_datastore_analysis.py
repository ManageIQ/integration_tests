# -*- coding: utf-8 -*-

from cfme import test_requirements
from cfme.configure.tasks import is_datastore_analysis_finished
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import datastore, host
from cfme.web_ui import toolbar as tb, Quadicon, InfoBlock
from utils import conf, testgen
from utils.blockers import BZ
from utils.wait import wait_for
import pytest

pytestmark = [test_requirements.smartstate]
DATASTORE_TYPES = ('vmfs', 'nfs', 'iscsi')
PROVIDER_TYPES = ('virtualcenter', 'rhevm')


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
    new_idlist = []
    new_argvalues = []

    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, PROVIDER_TYPES, required_fields=['datastores'])
    argnames += ['datastore']

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        datastores = args['provider'].data.get('datastores', {})
        if not datastores:
            continue
        for ds in datastores:
            if not ds.get('test_fleece', False):
                continue
            assert ds.get('type', None) in DATASTORE_TYPES,\
                'datastore type must be set to [{}] for smartstate analysis tests'\
                .format('|'.join(DATASTORE_TYPES))
            argvs = argvalues[i][:]
            new_argvalues.append(argvs + [datastore.Datastore(ds['name'], args['provider'].key,
                ds['type'])])
            test_id = '{}-{}'.format(args['provider'].key, ds['type'])
            new_idlist.append(test_id)
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


# TODO add support for events
@pytest.mark.tier(2)
@pytest.mark.meta(
    blockers=[
        BZ(1091033, unblock=lambda datastore: datastore.type != 'iscsi'),
        BZ(1180467, unblock=lambda provider: provider.type != 'rhevm'),
        BZ(1380707)
    ]
)
def test_run_datastore_analysis(request, setup_provider, provider, datastore, soft_assert):
    """Tests smarthost analysis

    Metadata:
        test_flag: datastore_analysis
    """

    # Check if there is a host with valid credentials
    host_names = datastore.get_hosts()
    assert len(host_names) != 0, "No hosts attached to this datastore found"
    for host_name in host_names:
        host_qi = Quadicon(host_name, 'host')
        if 'checkmark' in host_qi.creds:
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
            .format(datastore.name)

    # TODO add support for events
    # register_event(
    #     None,
    #     "datastore",
    #     datastore_name,
    #     ["datastore_analysis_request_req", "datastore_analysis_complete_req"]
    # )

    # Initiate analysis
    datastore.run_smartstate_analysis()
    wait_for(lambda: is_datastore_analysis_finished(datastore.name),
             delay=15, timeout="15m", fail_func=lambda: tb.select('Reload the current display'))

    ds_str = "Datastores Type"
    c_datastore = datastore.get_detail('Properties', ds_str)
    # Check results of the analysis and the datastore type
    soft_assert(c_datastore == datastore.type.upper(),
                'Datastore type does not match the type defined in yaml:' +
                'expected "{}" but was "{}"'.format(datastore.type.upper(), c_datastore))
    for row_name in CONTENT_ROWS_TO_CHECK:
        value = InfoBlock('Content', row_name).text
        soft_assert(value != '0',
                    'Expected value for {} to be non-empty'.format(row_name))
