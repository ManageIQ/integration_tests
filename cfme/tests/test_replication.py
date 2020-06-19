from time import sleep

import fauxfactory
import pytest
from wait_for import wait_for
from widgetastic.exceptions import RowNotFound

from cfme import test_requirements
from cfme.base.ui import LoginPage
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.configure.configuration.region_settings import ReplicationGlobalView
from cfme.fixtures.cli import provider_app_crud
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.virtual_machines import InfraVmDetailsView
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.rest import ViaREST
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import ViaUI
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.rest import assert_response

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

    def get_tabel_data(widget):
        ret = [row.name.text for row in widget.contents]
        logger.info("Widget text data:{%s}" % ret)
        return ret

    def data_check(view, table):
        return bool(get_tabel_data(view.dashboards("Default Dashboard").widgets(table)))

    view = navigate_to(remote_app.server, "Dashboard")
    for table_name in data_items:
        logger.info("Table name:{%s}" % table_name)
        wait_for(
            data_check, func_args=[view, table_name], delay=20, num_sec=600,
            fail_func=view.dashboards("Default Dashboard").browser.refresh,
            message=f"Waiting for table data item: {table_name} "
        )
        remote_app_data[table_name] = get_tabel_data(view.dashboards(
            "Default Dashboard").widgets(table_name))

    view = navigate_to(global_app.server, "Dashboard")
    for table_name in data_items:
        logger.info("Table name:{%s}" % table_name)
        wait_for(
            data_check, func_args=[view, table_name], delay=20, num_sec=600,
            fail_func=view.dashboards("Default Dashboard").browser.refresh,
            message=f"Waiting for table data item: {table_name}"
        )

        global_app_data[table_name] = get_tabel_data(view.dashboards(
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


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_replication_between_regions(provider, replicated_appliances):
    """Test that a provider added to the remote appliance is replicated to the global
    appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    with remote_appliance:
        provider.create()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    with global_appliance:
        global_appliance.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_replication_database_disconnection(provider, replicated_appliances):
    """Test that a provider created on the remote appliance *after* a database restart on the
    global appliance is still successfully replicated to the global appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    global_appliance.db_service.stop()
    sleep(60)
    global_appliance.db_service.start()

    with remote_appliance:
        provider.create()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    with global_appliance:
        global_appliance.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_replication_database_disconnection_with_backlog(provider, replicated_appliances):
    """Test that a provider created on the remote appliance *before* a database restart on the
    global appliance is still successfully replicated to the global appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    with remote_appliance:
        provider.create()
        global_appliance.db_service.stop()
        sleep(60)
        global_appliance.db_service.start()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    with global_appliance:
        global_appliance.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(automates=[1796681])
def test_replication_remote_down(replicated_appliances):
    """Test that the Replication tab displays in the global appliance UI when the remote appliance
    database cannot be reached.

    Bugzilla:
        1796681

    Metadata:
        test_flag: replication

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    with global_appliance:
        global_region = global_appliance.server.zone.region
        assert global_region.replication.get_replication_status(host=remote_appliance.hostname), (
            "Remote appliance not found on Replication tab after initial configuration.")

        result = global_appliance.ssh_client.run_command(
            f"firewall-cmd --direct --add-rule ipv4 filter OUTPUT 0 -d {remote_appliance.hostname}"
            " -j DROP")
        assert result.success, "Could not create firewall rule on global appliance."

        global_appliance.browser.widgetastic.refresh()
        assert global_region.replication.get_replication_status(host=remote_appliance.hostname), (
            "Remote appliance not found on Replication tab after dropped connection.")

    global_appliance.browser.widgetastic.refresh()
    assert global_region.replication.get_replication_status(host=remote_appliance.hostname), (
        "Remote appliance not found on Replication tab after dropped connection.")


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1678142])
@pytest.mark.ignore_stream('upstream')
def test_replication_connect_to_vm_in_region(provider, replicated_appliances):
    """Test that the user can view the VM in the global appliance UI, click on the
    "Connect to VM in its Region" button, and be redirected to the VM in the remote appliance UI.

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
        startsin: 5.11
    """
    remote_appliance, global_appliance = replicated_appliances

    vm_name = provider.data['cap_and_util']['chargeback_vm']

    vm_per_appliance = {
        a: a.provider_based_collection(provider).instantiate(vm_name, provider)
        for a in replicated_appliances
    }
    with remote_appliance:
        provider.create()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    with global_appliance:
        view = navigate_to(vm_per_appliance[global_appliance], 'Details')
        initial_count = len(view.browser.window_handles)
        main_window = view.browser.current_window_handle

        view.entities.summary('Multi Region').click_at('Remote Region')

        wait_for(
            lambda: len(view.browser.window_handles) > initial_count,
            timeout=30,
            message="Check for new browser window",
        )
        open_url_window = (set(view.browser.window_handles) - {main_window}).pop()
        view.browser.switch_to_window(open_url_window)

        # TODO: Remove this once `ensure_page_safe()` is equipped to handle WebDriverException
        # When a new window opens, URL takes time to load, this will act as a workaround.
        sleep(5)

        view = global_appliance.browser.create_view(LoginPage)
        wait_for(lambda: view.is_displayed, message="Wait for Login page")
        view.fill({
            'username': credentials['default']['username'],
            'password': credentials['default']['password']
        })
        view.login.click()

        # Use VM instantiated on global_appliance here because we're still using the same browser.
        view = vm_per_appliance[global_appliance].create_view(InfraVmDetailsView)
        wait_for(lambda: view.is_displayed, message="Wait for VM Details page")


@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_zones(replicated_appliances):
    """
    Verify that no remote zones can be selected when changing the server's zone
    in the global appliance UI.

    Bugzilla:
        1470283

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
    """
    remote_appliance, global_appliance = replicated_appliances

    remote_zone = 'remote-A'
    remote_appliance.collections.zones.create(name=remote_zone, description=remote_zone)

    global_zone = 'global-A'
    global_appliance.collections.zones.create(name=global_zone, description=global_zone)

    with global_appliance:
        view = navigate_to(global_appliance.server, 'Server')
        global_zones = [o.text for o in view.basic_information.appliance_zone.all_options]
        assert global_zone in global_zones and remote_zone not in global_zones


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.provider([CloudProvider, InfraProvider], selector=ONE_PER_TYPE)
@test_requirements.multi_region
@test_requirements.power
def test_replication_vm_power_control(provider, create_vm, context, replicated_appliances):
    """Test that the global appliance can power off a VM managed by the remote appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    vm_per_appliance = {
        a: a.provider_based_collection(provider).instantiate(create_vm.name, provider)
        for a in replicated_appliances
    }

    with remote_appliance:
        assert provider.create(validate_inventory=True), "Could not create provider."

    with global_appliance:
        vm = vm_per_appliance[global_appliance]
        if context.name == 'UI':
            vm.power_control_from_cfme(option=vm.POWER_OFF, cancel=False)
        else:
            vm_entity = global_appliance.rest_api.collections.vms.get(name=vm.name)
            global_appliance.rest_api.collections.vms.action.stop(vm_entity)
            assert_response(global_appliance, task_wait=0)

    with remote_appliance:
        vm = vm_per_appliance[remote_appliance]
        vm.wait_for_vm_state_change(desired_state=vm.STATE_OFF, timeout=900)
        assert vm.find_quadicon().data['state'] == 'off', "Incorrect VM quadicon state"
        assert not vm.mgmt.is_running, "VM is still running"
