import pytest
from widgetastic_patternfly import DropdownDisabled

from cfme import test_requirements
from cfme.exceptions import MenuItemNotFound
from cfme.infrastructure.datastore import Datastore
from cfme.infrastructure.datastore import DatastoreCollection
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import GH
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


@pytest.fixture
def datastore(setup_provider_modscope, temp_appliance_preconfig_funcscope, provider, datastore_type, datastore_name)\
        -> Datastore:
    with temp_appliance_preconfig_funcscope as appliance:
        return appliance.collections.datastores.instantiate(name=datastore_name,
                                                            provider=provider,
                                                            type=datastore_type)


@pytest.fixture
def datastores(temp_appliance_preconfig_funcscope, provider) -> DatastoreCollection:
    return temp_appliance_preconfig_funcscope.collections.datastores


@pytest.fixture
def datastores_hosts_setup(setup_provider_temp_appliance, provider, datastore):
    updated_hosts = []
    for host in datastore.hosts.all():
        try:
            host_data, = [data
                          for data in provider.data.get("hosts", {})
                          if data.get("name") == host.name]
        except ValueError as exc:
            pytest.skip(f"Data for host {host} in provider {provider} and datastore {datastore} "
                        f"couldn't be determined: {exc}.")
        else:
            host.update_credentials_rest(credentials=host_data['credentials'])
            updated_hosts.append(host)

    if not updated_hosts:
        pytest.skip(f"No hosts attached to the datastore {datastore} was selected for testing.")
    yield
    for host in updated_hosts:
        host.remove_credentials_rest()


@pytest.fixture()
def clear_all_tasks(appliance):
    # clear table
    col = appliance.collections.tasks.filter({'tab': 'AllTasks'})
    col.delete_all()


@pytest.mark.tier(2)
def test_run_datastore_analysis(setup_provider_temp_appliance, datastore, datastores, soft_assert,
                                clear_all_tasks, temp_appliance_preconfig_funcscope):
    """Tests smarthost analysis

    Metadata:
        test_flag: datastore_analysis

    Polarion:
        assignee: nansari
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/3h
    """
    temp_appliance_preconfig_funcscope.browser_steal = True;
    with temp_appliance_preconfig_funcscope as appliance:
        # Initiate analysis
        # try:

        # Note that it would be great to test both navigation paths.
        if GH(('ManageIQ/manageiq', 20367)).blocks:
            datastore.run_smartstate_analysis_from_provider()
        else:
            datastore.run_smartstate_analysis()

        #except (MenuItemNotFound, DropdownDisabled):
        #    # TODO need to update to cover all detastores
        #    pytest.skip(f'Smart State analysis is disabled for {datastore.name} datastore')
        details_view = navigate_to(datastore, 'DetailsFromProvider')
        # c_datastore = details_view.entities.properties.get_text_of("Datastore Type")

        # Check results of the analysis and the datastore type
        # TODO need to clarify datastore type difference
        # soft_assert(c_datastore == datastore.type.upper(),
        #             'Datastore type does not match the type defined in yaml:' +
        #             'expected "{}" but was "{}"'.format(datastore.type.upper(), c_datastore))

        if datastore.provider.one_of(RHEVMProvider) and GH(('ManageIQ/manageiq', 20366)).blocks or
            # TODO (jhenner) why is thati?
            (datastore.provider.one_of(VMwareProvider) and Version(datastore.provider.version) == '6.5'):
            return

        wait_for(lambda: details_view.entities.content.get_text_of(CONTENT_ROWS_TO_CHECK[0]),
                 delay=15, timeout="6m",
                 fail_condition='0',
                 fail_func=appliance.server.browser.refresh)

        managed_vms = details_view.entities.relationships.get_text_of('Managed VMs')
        if managed_vms != '0':
            for row_name in CONTENT_ROWS_TO_CHECK:
                value = details_view.entities.content.get_text_of(row_name)
                soft_assert(value != '0',
                            f'Expected value for {row_name} to be non-empty')
        else:
            assert details_view.entities.content.get_text_of(CONTENT_ROWS_TO_CHECK[-1]) != '0'
