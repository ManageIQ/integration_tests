# -*- coding: utf-8 -*-
import pytest
from widgetastic_patternfly import DropdownDisabled

from cfme import test_requirements
from cfme.exceptions import MenuItemNotFound
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
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
        metafunc,
        [RHEVMProvider, VMwareProvider],
        required_fields=['datastores']
    )
    argnames.append('datastore_type')
    argnames.append('datastore_name')
    new_idlist = []
    new_argvalues = []

    for index, argvalue_tuple in enumerate(argvalues):
        args = dict(list(zip(argnames, argvalue_tuple)))
        provider_arg = args["provider"]
        datastores = provider_arg.data.get("datastores", {})
        # don't collect any datastores without test_fleece set
        # only collect datastores with type matching accepted list
        testable_datastores = [
            (ds.get("type"), ds.get("name"))
            for ds in datastores
            if ds.get('test_fleece', False) and ds.get("type") in DATASTORE_TYPES
        ]
        for ds_type, ds_name in testable_datastores:
            new_argvalues.append([provider_arg, ds_type, ds_name])
            new_idlist.append(f"{idlist[index]}-{ds_type}")
        else:
            logger.warning(f"No testable datastores found for SSA on {provider_arg}")

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope='module')
def datastore(appliance, provider, datastore_type, datastore_name):
    return appliance.collections.datastores.instantiate(name=datastore_name,
                                                        provider=provider,
                                                        type=datastore_type)


@pytest.fixture(scope='module')
def datastores_hosts_setup(provider, datastore):
    hosts = datastore.hosts.all()
    for host in hosts:
        host_data = [data
                     for data in provider.data.get("hosts", {})
                     if data.get("name") == host.name]
        if not host_data:
            pytest.skip(f"No host data for provider {provider} and datastore {datastore}")
        host.update_credentials_rest(credentials=host_data[0]['credentials'])
    else:
        pytest.skip(f"No hosts attached to the datastore selected for testing: {datastore}")
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
    except (MenuItemNotFound, DropdownDisabled):
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
