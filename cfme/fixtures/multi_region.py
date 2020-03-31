import attr
import pytest


@attr.s
class ApplianceCluster:
    """
    Holder for Multi-Region appliances setup.
    Appliance from global region is stored in global_appliance.
    Whereas remote region appliances are stored in remote_appliances property.
    """
    global_appliance = attr.ib(default=None)
    remote_appliances = attr.ib(default=[])


@pytest.fixture(scope='module')
def multi_region_cluster(temp_appliances_unconfig_modscope_rhevm):
    # todo: make it work for all appliance types
    appliances = temp_appliances_unconfig_modscope_rhevm
    cluster = ApplianceCluster()

    cluster.global_appliance = appliances[0]
    cluster.remote_appliances = appliances[1:]
    yield cluster


@pytest.fixture(scope='module')
def setup_global_appliance(multi_region_cluster, app_creds_modscope):
    global_app = multi_region_cluster.global_appliance

    app_params = dict(region=99, dbhostname='localhost', username=app_creds_modscope['username'],
                      password=app_creds_modscope['password'], dbname='vmdb_production',
                      dbdisk=global_app.unpartitioned_disks[0])
    global_app.appliance_console_cli.configure_appliance_internal(**app_params)
    global_app.evmserverd.wait_for_running()
    global_app.wait_for_web_ui()


@pytest.fixture(scope='module')
def setup_remote_appliances(multi_region_cluster, setup_global_appliance, app_creds_modscope):
    remote_apps = multi_region_cluster.remote_appliances
    gip = multi_region_cluster.global_appliance.hostname
    for num, app in enumerate(remote_apps):
        region_n = str((num + 1) * 10)
        app_params = dict(region=region_n, dbhostname='localhost',
                          username=app_creds_modscope['username'],
                          password=app_creds_modscope['password'],
                          dbname='vmdb_production',
                          dbdisk=app.unpartitioned_disks[0],
                          fetch_key=gip,
                          sshlogin=app_creds_modscope['sshlogin'],
                          sshpass=app_creds_modscope['sshpass'])
        app.appliance_console_cli.configure_appliance_internal_fetch_key(**app_params)
        app.evmserverd.wait_for_running()
        app.wait_for_web_ui()
        app.set_pglogical_replication(replication_type=':remote')


@pytest.fixture(scope='module')
def setup_multi_region_cluster(multi_region_cluster, setup_remote_appliances,
                               setup_global_appliance):
    global_app = multi_region_cluster.global_appliance
    global_app.set_pglogical_replication(replication_type=':global')
    for app in multi_region_cluster.remote_appliances:
        global_app.add_pglogical_replication_subscription(app.hostname)


@pytest.fixture(scope='function')
def setup_remote_provider(multi_region_cluster, setup_multi_region_cluster, provider):
    with multi_region_cluster.remote_appliances[0]:
        provider.create_rest()
        yield provider
        provider.delete_rest()


@pytest.fixture(scope='function')
def activate_global_appliance(multi_region_cluster):
    global_appliance = multi_region_cluster.global_appliance
    with global_appliance:
        yield
