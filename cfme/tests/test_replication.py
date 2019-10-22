import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.cli import provider_app_crud
from cfme.utils.conf import credentials


pytestmark = [test_requirements.replication]


def setup_replication(remote_app, global_app):
    """Configure global_app database with region number 99 and subscribe to remote_app."""
    app_creds = {
        "username": credentials["database"]["username"],
        "password": credentials["database"]["password"],
        "sshlogin": credentials["ssh"]["username"],
        "sshpass": credentials["ssh"]["password"],
    }
    app_params = dict(region=99, dbhostname='localhost', username=app_creds['username'],
                      password=app_creds['password'], dbname='vmdb_production',
                      dbdisk=global_app.unpartitioned_disks[0], fetch_key=remote_app.hostname,
                      sshlogin=app_creds['sshlogin'], sshpass=app_creds['sshpass'])

    global_app.appliance_console_cli.configure_appliance_internal_fetch_key(**app_params)
    global_app.evmserverd.wait_for_running()
    global_app.wait_for_web_ui()

    remote_app.set_pglogical_replication(replication_type=':remote')
    global_app.set_pglogical_replication(replication_type=':global')
    global_app.add_pglogical_replication_subscription(remote_app.hostname)


@pytest.mark.provider([OpenStackProvider])
def test_replication_powertoggle(request, provider, configured_appliance, unconfigured_appliance):
    """
    power toggle from global to remote

    Polarion:
        assignee: mnadeem
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
.
    """
    instance_name = "test_replication_{}".format(fauxfactory.gen_alphanumeric().lower())
    remote_app = configured_appliance
    global_app = unconfigured_appliance

    provider_app_crud(OpenStackProvider, remote_app).setup()
    setup_replication(remote_app, global_app)

    remote_instance = remote_app.collections.cloud_instances.create_rest(instance_name, provider)
    request.addfinalizer(lambda: remote_instance.delete())

    global_instance = global_app.collections.cloud_instances.instantiate(instance_name, provider)
    remote_instance.wait_for_instance_state_change(desired_state=remote_instance.STATE_ON)

    global_instance = global_app.collections.cloud_instances.instantiate(instance_name, provider)

    # Power OFF instance using global appliance
    global_instance.power_control_from_cfme(option=global_instance.STOP)

    # Assert instance power off state from both remote and global appliance
    assert global_instance.wait_for_instance_state_change(
        desired_state=global_instance.STATE_OFF).out
    assert remote_instance.wait_for_instance_state_change(
        desired_state=remote_instance.STATE_OFF).out

    # Power ON instance using global appliance
    global_instance.power_control_from_cfme(option=global_instance.START)

    # Assert instance power ON state from both remote and global appliance
    assert global_instance.wait_for_instance_state_change(
        desired_state=global_instance.STATE_ON).out
    assert remote_instance.wait_for_instance_state_change(
        desired_state=global_instance.STATE_ON).out


@pytest.mark.tier(2)
def test_replication_appliance_add_single_subscription(configured_appliance,
                                                       unconfigured_appliance):
    """
    Add one remote subscription to global region

    Polarion:
        assignee: mnadeem
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
    remote_app = configured_appliance
    global_app = unconfigured_appliance
    region = global_app.collections.regions.instantiate()

    setup_replication(remote_app, global_app)
    assert region.replication.get_replication_status(host=remote_app.hostname)


@pytest.mark.manual
@pytest.mark.tier(3)
def test_replication_delete_remote_from_global():
    """
    Delete remote subscription from global region

    Polarion:
        assignee: mnadeem
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
    pass


@pytest.mark.manual
def test_replication_low_bandwidth():
    """
    ~5MB/s up/down

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_replication_re_add_deleted_remote():
    """
    Re-add deleted remote region

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/12h
        testSteps:
            1. Have A Remote subscribed to Global.
            2. Remove the Remote subscription from Global.
            3. Add the Remote to Global again
        expectedResults:
            1.
            2. No error. Appliance subscribed.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_remote_to_global_by_ip_pglogical():
    """
    Test replication from remote region to global using any data type
    (provider,event,etc)

    Polarion:
        assignee: mnadeem
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
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_appliance_set_type_global_ui():
    """
    Set appliance replication type to "Global" and add subscription in the
    UI

    Polarion:
        assignee: mnadeem
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
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_replication_appliance_add_multi_subscription():
    """
    add two or more subscriptions to global

    Polarion:
        assignee: mnadeem
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
    pass


@pytest.mark.manual
def test_replication_network_dropped_packets():
    """
    10% dropped packets

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_global_region_dashboard():
    """
    Global dashboard show remote data

    Polarion:
        assignee: mnadeem
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
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_global_to_remote_new_vm_from_template():
    """
    Create a new VM from template in remote region from global region

    Polarion:
        assignee: mnadeem
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
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_subscription_revalidation_pglogical():
    """
    Subscription validation passes for replication subscriptions which
    have been validated and successfully saved.

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Attempt to validate the subscription
        expectedResults:
            1. Validation succeeds as this subscription was successfully
               saved and is currently replicating
    """
    pass
