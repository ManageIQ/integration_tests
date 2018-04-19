# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.exceptions import MenuItemNotFound
from cfme.infrastructure.host import Host, get_credentials_from_config
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen, hosts
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
        args = dict(zip(argnames, argvalue_tuple))
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
def datastores_hosts_setup(provider, datastore, request, appliance):
    # Check if there is a host with valid credentials
    host_entities = datastore.get_hosts()
    assert len(host_entities) != 0, "No hosts attached to this datastore found"
    for host_entity in host_entities:
        if 'checkmark' in host_entity.data['creds']:
            continue
        # If not, get credentials for one of the present hosts
        host_data = hosts.get_host_data_by_name(provider.key, host_entity.name)
        if host_data is None:
            continue
        host_collection = appliance.collections.hosts
        test_host = host_collection.instantiate(name=host_entity.name, provider=provider)
        test_host.update_credentials_rest(
            credentials=get_credentials_from_config(host_data.credentials))
        request.addfinalizer(lambda: test_host.update_credentials_rest(
            credentials=Host.Credential(principal="", secret="")))


@pytest.fixture(scope='function')
def clear_all_tasks(appliance):
    destination = 'AllTasks' if appliance.version >= '5.9' else 'AllOtherTasks'
    # clear table
    appliance.collections.tasks.switch_tab(destination).delete_all()


@pytest.mark.tier(2)
def test_run_datastore_analysis(setup_provider, datastore, soft_assert, datastores_hosts_setup,
                                clear_all_tasks, appliance):
    """Tests smarthost analysis

    Metadata:
        test_flag: datastore_analysis
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
