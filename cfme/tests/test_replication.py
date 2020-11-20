import fauxfactory
import pytest
from wait_for import wait_for
from widgetastic.exceptions import RowNotFound

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.configure.configuration.region_settings import ReplicationGlobalAddView
from cfme.configure.configuration.region_settings import ReplicationGlobalView
from cfme.fixtures.cli import provider_app_crud
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.log import logger

pytestmark = [test_requirements.replication, pytest.mark.long_running]


def create_vm(provider, vm_name):
    collection = provider.appliance.provider_based_collection(provider)
    try:
        template_name = provider.data['templates']['full_template']['name']
    except KeyError:
        pytest.skip(f'Unable to identify full_template for provider: {provider}')

    vm = collection.instantiate(
        vm_name,
        provider,
        template_name=template_name
    )
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm


def are_dicts_same(dict1, dict2):
    logger.info(f"Comparing two dictionaries\n dict1:{dict1}\n dict2:{dict2}")
    if set(dict1) != set(dict2):
        return False
    for key in dict1.keys():
        if set(dict1[key]) != set(dict2[key]):
            return False
    return True


@pytest.fixture
def setup_replication(configured_appliance, unconfigured_appliance):
    """Configure global_app database with region number 99 and subscribe to remote_app."""
    remote_app, global_app = configured_appliance, unconfigured_appliance
    app_params = dict(
        region=99,
        dbhostname='localhost',
        username=credentials["database"]["username"],
        password=credentials["database"]["password"],
        dbname='vmdb_production',
        dbdisk=global_app.unpartitioned_disks[0],
        fetch_key=remote_app.hostname,
        sshlogin=credentials["ssh"]["username"],
        sshpass=credentials["ssh"]["password"],
    )

    global_app.appliance_console_cli.configure_appliance_internal_fetch_key(**app_params)
    global_app.evmserverd.wait_for_running()
    global_app.wait_for_miq_ready()

    remote_app.set_pglogical_replication(replication_type=':remote')
    global_app.set_pglogical_replication(replication_type=':global')
    global_app.add_pglogical_replication_subscription(remote_app.hostname)

    return configured_appliance, unconfigured_appliance


@pytest.mark.provider([OpenStackProvider])
def test_replication_powertoggle(request, provider, setup_replication, small_template):
    """
    power toggle from global to remote

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/12h
        testSteps:
            1. Have a VM created in the provider in the Remote region
               subscribed to Global.
            2. Turn the VM off using the Global appliance.
            3. Turn the VM on using the Global appliance.
        expectedResults:
            1.
            2. VM state changes to off in the Remote and Global appliance.
            3. VM state changes to on in the Remote and Global appliance.
    """
    instance_name = fauxfactory.gen_alphanumeric(start="test_replication_", length=25).lower()
    remote_app, global_app = setup_replication

    provider.appliance = remote_app
    provider.setup()

    remote_instance = remote_app.collections.cloud_instances.instantiate(
        instance_name, provider, small_template.name
    )
    global_instance = global_app.collections.cloud_instances.instantiate(instance_name, provider)

    # Create instance
    remote_instance.create_on_provider(find_in_cfme=True)
    request.addfinalizer(remote_instance.cleanup_on_provider)

    remote_instance.wait_for_instance_state_change(desired_state=remote_instance.STATE_ON)

    # Power OFF instance using global appliance
    global_instance.power_control_from_cfme(option=global_instance.STOP)

    # Assert instance power off state from both remote and global appliance
    assert global_instance.wait_for_instance_state_change(
        desired_state=global_instance.STATE_OFF
    ).out
    assert remote_instance.wait_for_instance_state_change(
        desired_state=remote_instance.STATE_OFF
    ).out

    # Power ON instance using global appliance
    global_instance.power_control_from_cfme(option=global_instance.START)

    # Assert instance power ON state from both remote and global appliance
    assert global_instance.wait_for_instance_state_change(
        desired_state=global_instance.STATE_ON
    ).out
    assert remote_instance.wait_for_instance_state_change(
        desired_state=global_instance.STATE_ON
    ).out


@pytest.mark.tier(2)
def test_replication_appliance_add_single_subscription(setup_replication):
    """

    Add one remote subscription to global region

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/12h
        startsin: 5.7
        testSteps:
            1. Configure first appliance as Global.
            2. Configure second appliance as Remote, subscribed to Global.
        expectedResults:
            1.
            2. No error. Appliance subscribed.
    """
    remote_app, global_app = setup_replication
    region = global_app.collections.regions.instantiate()
    assert region.replication.get_replication_status(host=remote_app.hostname)


@pytest.mark.tier(3)
def test_replication_re_add_deleted_remote(setup_replication):
    """
    Re-add deleted remote region

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        initialEstimate: 1/12h
        testSteps:
            1. Have A Remote subscribed to Global.
            2. Remove the Remote subscription from Global.
            3. Add the Remote to Global again
        expectedResults:
            1.
            2. Subscription is successfully removed.
            3. No error. Appliance subscribed.
    """
    remote_app, global_app = setup_replication
    region = global_app.collections.regions.instantiate()

    # Remove the Remote subscription from Global and make sure it is removed
    region.replication.remove_global_appliance(host=remote_app.hostname)
    with pytest.raises(RowNotFound):
        region.replication.get_replication_status(host=remote_app.hostname)

    # Add the Remote to Global again
    global_app.set_pglogical_replication(replication_type=":global")
    global_app.add_pglogical_replication_subscription(remote_app.hostname)

    # Assert the hostname is present
    view = region.replication.create_view(ReplicationGlobalView)
    view.browser.refresh()
    assert region.replication.get_replication_status(host=remote_app.hostname)


@pytest.mark.tier(3)
def test_replication_delete_remote_from_global(setup_replication):
    """
    Delete remote subscription from global region

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/5h
        testSteps:
            1. Have A Remote subscribed to Global.
            2. Remove the Remote subscription from Global.
        expectedResults:
            1.
            2. No error. Appliance unsubscribed.
    """
    remote_app, global_app = setup_replication
    region = global_app.collections.regions.instantiate()

    # Remove the Remote subscription from Global
    region.replication.remove_global_appliance(host=remote_app.hostname)
    with pytest.raises(RowNotFound):
        region.replication.get_replication_status(host=remote_app.hostname)


@pytest.mark.tier(1)
def test_replication_remote_to_global_by_ip_pglogical(setup_replication):
    """
    Test replication from remote region to global using any data type
    (provider,event,etc)

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.6
        testSteps:
            1. Have A Remote subscribed to Global.
            2. Create a provider in remote region.
            3. Check the provider appeared in the Global.
        expectedResults:
            1.
            2.
            3. Provider appeared in the Global.
    """
    remote_app, global_app = setup_replication
    provider = provider_app_crud(OpenStackProvider, remote_app)
    provider.setup()

    # Assert the provider is replicated to global appliance
    assert provider.name in global_app.managed_provider_names, "Provider name not found"


@pytest.mark.tier(1)
def test_replication_appliance_set_type_global_ui(configured_appliance, unconfigured_appliance):
    """
    Set appliance replication type to "Global" and add subscription in the
    UI

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/6h
        testtype: functional
        testSteps:
            1. Have two appliances with same v2 keys and different regions
            2. Set one as Global and the other as Remote and add subscribe the
               Remote to the Global
        expectedResults:
            1.
            2. No error, appliance subscribed.
    """
    remote_app, global_app = configured_appliance, unconfigured_appliance
    app_params = dict(
        region=99,
        dbhostname='localhost',
        username=credentials["database"]["username"],
        password=credentials["database"]["password"],
        dbname='vmdb_production',
        dbdisk=global_app.unpartitioned_disks[0],
        fetch_key=remote_app.hostname,
        sshlogin=credentials["ssh"]["username"],
        sshpass=credentials["ssh"]["password"],
    )

    global_app.appliance_console_cli.configure_appliance_internal_fetch_key(**app_params)
    global_app.evmserverd.wait_for_running()
    global_app.wait_for_miq_ready()

    # Making configured app to Remote Appliance using UI
    remote_region = remote_app.collections.regions.instantiate()
    remote_region.replication.set_replication(replication_type="remote")

    # Adding Remote Appliance into Global appliance using UI
    global_region = global_app.collections.regions.instantiate(number=99)
    global_region.replication.set_replication(
        replication_type="global", updates={"host": remote_app.hostname}, validate=True)

    # Validating replication
    assert global_region.replication.get_replication_status(
        host=remote_app.hostname), "Replication is not started."


@pytest.mark.tier(2)
@pytest.mark.parametrize("temp_appliances_unconfig_modscope_rhevm", [3], indirect=True)
def test_replication_appliance_add_multi_subscription(request, setup_multi_region_cluster,
                                                      multi_region_cluster,
                                                      temp_appliances_unconfig_modscope_rhevm):
    """
    add two or more subscriptions to global

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        initialEstimate: 1/4h
        startsin: 5.7
        testSteps:
            1. Have three appliances with same v2 keys and different regions
            2. Set one as Global and the other two as Remote and add subscribe
               the Remotes to the Global
        expectedResults:
            1.
            2. appliances subscribed.
    """
    region = multi_region_cluster.global_appliance.collections.regions.instantiate()
    navigate_to(region.replication, "Global")
    for host in multi_region_cluster.remote_appliances:
        assert region.replication.get_replication_status(
            host=host.hostname
        ), f"{host.hostname} Remote Appliance is not found in Global Appliance's list"


@pytest.mark.tier(1)
def test_replication_global_region_dashboard(request, setup_replication):
    """
    Global dashboard show remote data

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        initialEstimate: 1/4h
        testSteps:
            1. Have a VM created in the provider in the Remote region which is
               subscribed to Global.
            2. Check the dashboard on the Global shows data from the Remote region.
        expectedResults:
            1.
            2. Dashboard on the Global displays data from the Remote region
    """
    remote_app, global_app = setup_replication
    remote_provider = provider_app_crud(InfraProvider, remote_app)
    remote_provider.setup()
    assert remote_provider.name in remote_app.managed_provider_names, "Provider is not available."

    new_vm_name = fauxfactory.gen_alphanumeric(start="test_rep_dashboard", length=25).lower()
    vm = create_vm(provider=remote_provider, vm_name=new_vm_name)
    request.addfinalizer(vm.cleanup_on_provider)
    data_items = ('EVM: Recently Discovered Hosts', 'EVM: Recently Discovered VMs',
                  'Top Storage Consumers')
    remote_app_data, global_app_data = {}, {}

    def get_table_data(widget):
        ret = [row.name.text for row in widget.contents]
        logger.info("Widget text data:{%s}" % ret)
        return ret

    def data_check(view, table):
        return bool(get_table_data(view.dashboards("Default Dashboard").widgets(table)))

    view = navigate_to(remote_app.server, "Dashboard")
    for table_name in data_items:
        logger.info("Table name:{%s}" % table_name)
        wait_for(
            data_check, func_args=[view, table_name], delay=20, num_sec=600,
            fail_func=view.dashboards("Default Dashboard").browser.refresh,
            message=f"Waiting for table data item: {table_name} "
        )
        remote_app_data[table_name] = get_table_data(view.dashboards(
            "Default Dashboard").widgets(table_name))

    view = navigate_to(global_app.server, "Dashboard")
    for table_name in data_items:
        logger.info("Table name:{%s}" % table_name)
        wait_for(
            data_check, func_args=[view, table_name], delay=20, num_sec=600,
            fail_func=view.dashboards("Default Dashboard").browser.refresh,
            message=f"Waiting for table data item: {table_name}"
        )

        global_app_data[table_name] = get_table_data(view.dashboards(
            "Default Dashboard").widgets(table_name))

    # TODO(ndhandre): Widget not implemented so some widget not checking in this test case they are
    #  'Vendor and Guest OS Chart', 'Top Memory Consumers (weekly)', 'Top CPU Consumers (weekly)',
    #  'Virtual Infrastructure Platforms', 'Guest OS Information'

    assert are_dicts_same(remote_app_data, global_app_data), "Dashboard is not same of both app."


@pytest.mark.tier(1)
def test_replication_global_to_remote_new_vm_from_template(request, setup_replication):
    """
    Create a new VM from template in remote region from global region

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/6h
        testSteps:
            1. Configure first appliance as Global.
            2. Configure second appliance as Remote, subscribed to Global.
            3. Create a VM from template in Remote region using the Global appliance.
        expectedResults:
            1.
            2.
            3. VM created in the Remote, no errors.
    """
    remote_app, global_app = setup_replication
    remote_provider = provider_app_crud(RHEVMProvider, remote_app)
    remote_provider.setup()
    assert remote_provider.name in remote_app.managed_provider_names, "Provider is not available."

    new_vm_name = fauxfactory.gen_alphanumeric(start="test_replication_", length=25).lower()
    global_provider = provider_app_crud(RHEVMProvider, global_app)
    vm = create_vm(provider=global_provider, vm_name=new_vm_name)
    request.addfinalizer(vm.cleanup_on_provider)
    remote_provider.refresh_provider_relationships()
    assert (remote_app.collections.infra_vms.instantiate(new_vm_name, remote_provider).exists), (
        f"{new_vm_name} vm is not found in Remote Appliance"
    )


@pytest.mark.tier(1)
def test_replication_subscription_revalidation_pglogical(configured_appliance,
                                                         unconfigured_appliance):
    """
    Subscription validation passes for replication subscriptions which
    have been validated and successfully saved.

    Polarion:
        assignee: dgaikwad
        casecomponent: Replication
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Attempt to validate the subscription
        expectedResults:
            1. Validation succeeds as this subscription was successfully
               saved and is currently replicating
    """

    remote_app, global_app = configured_appliance, unconfigured_appliance
    app_params = dict(
        region=99,
        dbhostname='localhost',
        username=credentials["database"]["username"],
        password=credentials["database"]["password"],
        dbname='vmdb_production',
        dbdisk=global_app.unpartitioned_disks[0],
        fetch_key=remote_app.hostname,
        sshlogin=credentials["ssh"]["username"],
        sshpass=credentials["ssh"]["password"],
    )

    global_app.appliance_console_cli.configure_appliance_internal_fetch_key(**app_params)
    global_app.evmserverd.wait_for_running()
    global_app.wait_for_miq_ready()

    remote_app.set_pglogical_replication(replication_type=':remote')
    region = global_app.collections.regions.instantiate(number=99)
    region.replication.set_replication(replication_type="global",
                                       updates={"host": remote_app.hostname},
                                       validate=True)


@test_requirements.settings
@test_requirements.multi_region
@pytest.mark.tier(3)
def test_replication_subscription_update(multi_region_cluster, setup_multi_region_cluster):
    """
    Edit replication subscription

    Polarion:
        assignee: dgaikwad
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/4h
    """
    global_appliance = multi_region_cluster.global_appliance

    region = global_appliance.collections.regions.instantiate(number=99)

    # Update with bad password and verify that error flash message appears
    row = region.replication._global_replication_row()

    row[8].widget.click(handle_alert=True)

    view = region.replication.create_view(ReplicationGlobalAddView)
    view.fill({'username': 'bad_user'})
    view.accept_button.click()
    view.action_dropdown.item_select('Validate')
    view.flash.assert_message("FATAL: password authentication failed", partial=True, t='error')

    row[8].widget.click(handle_alert=True)

    view.fill({'username': credentials.database.username})
    view.accept_button.click()
    view.action_dropdown.item_select('Validate')
    view.flash.assert_success_message("Subscription Credentials validated successfully")
