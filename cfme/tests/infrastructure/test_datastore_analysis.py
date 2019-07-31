# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.exceptions import MenuItemNotFound
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.smartstate]
DATASTORE_TYPES = ('vmfs', 'nfs', 'iscsi')


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
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [RHEVMProvider, VMwareProvider], required_fields=['datastores'])
    argnames.append('datastore_type')
    new_idlist = []
    new_argvalues = []

    for index, argvalue_tuple in enumerate(argvalues):
        args = dict(list(zip(argnames, argvalue_tuple)))
        datastores = args['provider'].data.datastores
        for ds in datastores:
            if not ds.get('test_fleece', False):
                continue
            assert ds['type'] in DATASTORE_TYPES, (
                'datastore type must be set to [{}] for smartstate analysis tests'.format(
                    '|'.join(DATASTORE_TYPES)))
            new_argvalues.append([args["provider"], ds['type']])
            test_id = '{}-{}'.format(idlist[index], ds['type'])
            new_idlist.append(test_id)

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope='module')
def datastore(appliance, provider, datastore_type):
    datastores = provider.data.get('datastores')
    for ds in datastores:
        if ds.type == datastore_type:
            return appliance.collections.datastores.instantiate(
                name=ds.name, provider=provider, type=ds.type)


@pytest.fixture(scope='module')
def datastores_hosts_setup(provider, datastore):
    hosts = datastore.hosts.all()
    assert hosts, "No hosts attached to this datastore found"
    for host in hosts:
        host_data = [data for data in provider.data['hosts'] if data['name'] == host.name]
        if not host_data:
            pytest.skip("No host data")
        host.update_credentials_rest(credentials=host_data[0]['credentials'])
    yield
    for host in hosts:
        host.remove_credentials_rest()


@pytest.fixture(scope='function')
def clear_all_tasks(appliance):
    # clear table
    col = appliance.collections.tasks.filter({'tab': 'AllTasks'})
    col.delete_all()


@pytest.mark.tier(2)
def test_run_datastore_analysis(setup_provider, datastore, soft_assert, datastores_hosts_setup,
                                clear_all_tasks, appliance):
    """Tests smarthost analysis

    Metadata:
        test_flag: datastore_analysis

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/3h
    """
    # Initiate analysis
    try:
        datastore.run_smartstate_analysis(wait_for_task_result=True)
    except MenuItemNotFound:
        # TODO need to update to cover all detastores
        pytest.skip('Smart State analysis is disabled for {} datastore'.format(datastore.name))
    details_view = navigate_to(datastore, 'DetailsFromProvider')
    # c_datastore = details_view.entities.properties.get_text_of("Datastore Type")

    # Check results of the analysis and the datastore type
    # TODO need to clarify datastore type difference
    # soft_assert(c_datastore == datastore.type.upper(),
    #             'Datastore type does not match the type defined in yaml:' +
    #             'expected "{}" but was "{}"'.format(datastore.type.upper(), c_datastore))

    wait_for(lambda: details_view.entities.content.get_text_of(CONTENT_ROWS_TO_CHECK[0]),
             delay=15, timeout="3m",
             fail_condition='0',
             fail_func=appliance.server.browser.refresh)
    managed_vms = details_view.entities.relationships.get_text_of('Managed VMs')
    if managed_vms != '0':
        for row_name in CONTENT_ROWS_TO_CHECK:
            value = details_view.entities.content.get_text_of(row_name)
            soft_assert(value != '0',
                        'Expected value for {} to be non-empty'.format(row_name))
    else:
        assert details_view.entities.content.get_text_of(CONTENT_ROWS_TO_CHECK[-1]) != '0'
