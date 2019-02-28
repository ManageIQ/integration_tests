from collections import namedtuple
from contextlib import contextmanager

import fauxfactory
import pytest
from six import iteritems

import cfme.utils.auth as authutil
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.configure.configuration.region_settings import RedHatUpdates
from cfme.fixtures.appliance import sprout_appliances
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.test_framework.sprout.client import AuthException
from cfme.test_framework.sprout.client import SproutClient
from cfme.utils import conf
from cfme.utils.conf import auth_data
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.providers import list_providers_by_class
from cfme.utils.version import Version
from cfme.utils.wait import wait_for

TimedCommand = namedtuple("TimedCommand", ["command", "timeout"])


@pytest.fixture()
def unconfigured_appliance(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]


@pytest.fixture()
def unconfigured_appliance_secondary(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]


@pytest.fixture()
def unconfigured_appliances(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=3,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps


@pytest.fixture()
def configured_appliance(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=True,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]


@pytest.fixture(scope="function")
def dedicated_db_appliance(app_creds, unconfigured_appliance):
    """Commands:
    1. 'ap' launch appliance_console,
    2. '' clear info screen,
    3. '5' setup db,
    4. '1' Creates v2_key,
    5. '1' selects internal db,
    6. '1' use partition,
    7. 'y' create dedicated db,
    8. 'pwd' db password,
    9. 'pwd' confirm db password + wait 360 secs and
    10. '' finish."""
    app = unconfigured_appliance
    pwd = app_creds["password"]
    command_set = ("ap", "", "7", "1", "1", "2", "y", pwd, TimedCommand(pwd, 360), "")
    app.appliance_console.run_commands(command_set)
    wait_for(lambda: app.db.is_dedicated_active)
    yield app


@pytest.fixture(scope="function")
def appliance_with_preset_time(temp_appliance_preconfig_funcscope):
    """Grabs fresh appliance and sets time and date prior to running tests"""
    command_set = ("ap", "", "3", "y", "2020-10-20", "09:58:00", "y", "")
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)

    def date_changed():
        return temp_appliance_preconfig_funcscope.ssh_client.run_command(
            "date +%F-%T | grep 2020-10-20-09"
        ).success

    wait_for(date_changed)
    return temp_appliance_preconfig_funcscope


@pytest.fixture()
def ipa_crud():
    try:
        ipa_keys = [
            key
            for key, yaml in iteritems(auth_data.auth_providers)
            if yaml.type == authutil.FreeIPAAuthProvider.auth_type
        ]
        ipa_provider = authutil.get_auth_crud(ipa_keys[0])
    except AttributeError:
        pytest.skip("Unable to parse auth_data.yaml for freeipa server")
    except IndexError:
        pytest.skip("No freeipa server available for testing")
    logger.info("Configuring first available freeipa auth provider %s", ipa_provider)

    return ipa_provider


@pytest.fixture()
def app_creds():
    return {
        "username": credentials["database"]["username"],
        "password": credentials["database"]["password"],
        "sshlogin": credentials["ssh"]["username"],
        "sshpass": credentials["ssh"]["password"],
    }


@pytest.fixture(scope="module")
def app_creds_modscope():
    return {
        "username": credentials["database"]["username"],
        "password": credentials["database"]["password"],
        "sshlogin": credentials["ssh"]["username"],
        "sshpass": credentials["ssh"]["password"],
    }


@contextmanager
def get_apps(appliance, old_version, count, preconfigured, pytest_config):
    """Requests appliance from sprout based on old_versions, edits partitions and adds
        repo file for update"""
    series = appliance.version.series()
    update_url = "update_url_{}".format(series.replace(".", ""))
    usable = []
    sp = SproutClient.from_config(sprout_user_key=pytest_config.option.sprout_user_key or None)
    available_versions = set(sp.call_method("available_cfme_versions"))
    for a in available_versions:
        if a.startswith(old_version):
            usable.append(Version(a))
    usable_sorted = sorted(usable, key=lambda o: o.version)
    apps = []
    pool_id = None
    try:
        apps, pool_id = sp.provision_appliances(
            count=count,
            preconfigured=preconfigured,
            provider_type="rhevm",
            lease_time=180,
            version=str(usable_sorted[-1]),
        )
        urls = cfme_data["basic_info"][update_url]
        for app in apps:
            app.db.extend_partition()
            app.ssh_client.run_command(
                "curl {} -o /etc/yum.repos.d/update.repo".format(urls)
            )
        yield apps
    except AuthException:
        msg = ('Sprout credentials key or yaml maps missing or invalid,'
               'unable to provision appliance version %s'.format(str(usable_sorted[-1])))
        logger.exception(msg)
        pytest.skip(msg)
    finally:
        for app in apps:
            app.ssh_client.close()
        if pool_id:
            sp.destroy_pool(pool_id)


@pytest.fixture
def appliance_preupdate(appliance, old_version):
    """Requests single appliance from sprout."""
    with get_apps(appliance, old_version, count=1, preconfigured=True,
                  pytest_config=pytest.config) as apps:
        yield apps[0]


@pytest.fixture
def multiple_preupdate_appliances(appliance, old_version):
    """Requests multiple appliances from sprout."""
    with get_apps(appliance, old_version, count=2, preconfigured=False,
                  pytest_config=pytest.config) as apps:
        yield apps


@pytest.fixture
def ha_multiple_preupdate_appliances(appliance, old_version):
    """Requests multiple appliances from sprout."""
    with get_apps(appliance, old_version, count=3, preconfigured=False,
                  pytest_config=pytest.config) as apps:
        yield apps


@pytest.fixture
def ha_appliances_with_providers(ha_multiple_preupdate_appliances, app_creds):
    """Configure HA environment

    Appliance one configuring dedicated database, 'ap' launch appliance_console,
    '' clear info screen, '5' setup db, '1' Creates v2_key, '1' selects internal db,
    '1' use partition, 'y' create dedicated db, 'pwd' db password, 'pwd' confirm db password + wait
    360 secs and '' finish.

    Appliance two creating region in dedicated database, 'ap' launch appliance_console, '' clear
    info screen, '5' setup db, '2' fetch v2_key, 'app0_ip' appliance ip address, '' default user,
    'pwd' appliance password, '' default v2_key location, '2' create region in external db, '0' db
    region number, 'y' confirm create region in external db 'app0_ip', '' ip and default port for
    dedicated db, '' use default db name, '' default username, 'pwd' db password, 'pwd' confirm db
    password + wait 360 seconds and '' finish.

    Appliance one configuring primary node for replication, 'ap' launch appliance_console, '' clear
    info screen, '6' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait 360 seconds to configure, '' finish.


    Appliance three configuring standby node for replication, 'ap' launch appliance_console, ''
    clear info screen, '6' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait 360 seconds to configure, '' finish.


    Appliance two configuring automatic failover of database nodes, 'ap' launch appliance_console,
    '' clear info screen '9' configure application database failover monitor, '1' start failover
    monitor. wait 30 seconds for service to start '' finish.

    """
    apps0, apps1, apps2 = ha_multiple_preupdate_appliances
    app0_ip = apps0.hostname
    app1_ip = apps1.hostname
    pwd = app_creds["password"]
    # Configure first appliance as dedicated database
    command_set = ("ap", "", "5", "1", "1", "1", "y", pwd, TimedCommand(pwd, 360), "")
    apps0.appliance_console.run_commands(command_set)
    wait_for(lambda: apps0.db.is_dedicated_active)
    # Configure EVM webui appliance with create region in dedicated database
    command_set = ("ap", "", "5", "2", app0_ip, "", pwd, "", "2", "0", "y", app0_ip, "", "", "",
                   TimedCommand(pwd, 360), "")
    apps2.appliance_console.run_commands(command_set)
    apps2.wait_for_evm_service()
    apps2.wait_for_web_ui()
    # Configure primary replication node
    command_set = ("ap", "", "6", "1", "1", "", "", pwd, pwd, app0_ip, TimedCommand("y", 60),
                   "")
    apps0.appliance_console.run_commands(command_set)
    # Configure secondary replication node
    command_set = ("ap", "", "6", "2", "1", "2", "", "", pwd, pwd, app0_ip, app1_ip, "y",
                   TimedCommand("y", 90), "")
    apps1.appliance_console.run_commands(command_set)
    # Configure automatic failover on EVM appliance
    command_set = ("ap", "", "8", TimedCommand("1", 30), "")
    apps2.appliance_console.run_commands(command_set)

    def is_ha_monitor_started(appliance):
        return appliance.ssh_client.run_command(
            "grep {} /var/www/miq/vmdb/config/failover_databases.yml".format(app1_ip)
        ).success

    wait_for(
        is_ha_monitor_started, func_args=[apps2], timeout=300, handle_exception=True
    )
    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, apps2).setup()
    provider_app_crud(EC2Provider, apps2).setup()
    return ha_appliances_with_providers


@pytest.fixture
def replicated_appliances_with_providers(multiple_preupdate_appliances):
    """Returns two database-owning appliances, configures with providers."""
    appl1, appl2 = multiple_preupdate_appliances
    # configure appliances
    appl1.configure(region=0)
    appl1.wait_for_web_ui()
    appl2.configure(region=99)
    appl2.wait_for_web_ui()
    # configure replication between appliances
    appl1.set_pglogical_replication(replication_type=":remote")
    appl2.set_pglogical_replication(replication_type=":global")
    appl2.add_pglogical_replication_subscription(appl1.hostname)
    # Add infra/cloud providers
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(EC2Provider, appl1).setup()
    return multiple_preupdate_appliances


@pytest.fixture
def ext_appliances_with_providers(multiple_preupdate_appliances, app_creds_modscope):
    """Returns two database-owning appliances, configures first appliance with providers."""
    appl1, appl2 = multiple_preupdate_appliances
    app_ip = appl1.hostname
    # configure appliances
    appl1.configure(region=0)
    appl1.wait_for_web_ui()
    appl2.appliance_console_cli.configure_appliance_external_join(
        app_ip,
        app_creds_modscope["username"],
        app_creds_modscope["password"],
        "vmdb_production",
        app_ip,
        app_creds_modscope["sshlogin"],
        app_creds_modscope["sshpass"],
    )
    appl2.wait_for_web_ui()
    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(EC2Provider, appl1).setup()
    return multiple_preupdate_appliances


@pytest.fixture
def enabled_embedded_appliance(appliance_preupdate):
    """Takes a preconfigured appliance and enables the embedded ansible role"""
    appliance_preupdate.enable_embedded_ansible_role()
    assert appliance_preupdate.is_embedded_ansible_running
    return appliance_preupdate


@pytest.fixture
def appliance_with_providers(appliance_preupdate):
    """Adds providers to appliance"""
    appl1 = appliance_preupdate
    # Add infra/cloud providers
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(EC2Provider, appl1).setup()
    return appliance_preupdate


def provider_app_crud(provider_class, appliance):
    try:
        prov = list_providers_by_class(provider_class)[0]
        logger.info("using provider {}".format(prov.name))
        prov.appliance = appliance
        return prov
    except IndexError:
        pytest.skip("No {} providers available (required)".format(provider_class.type_name))


def provision_vm(request, provider):
    """Function to provision appliance to the provider being tested"""
    vm_name = "test_rest_db_{}".format(fauxfactory.gen_alphanumeric())
    coll = provider.appliance.provider_based_collection(provider, coll_type="vms")
    vm = coll.instantiate(vm_name, provider)
    request.addfinalizer(vm.delete)
    if not provider.mgmt.does_vm_exist(vm_name):
        logger.info("deploying %s on provider %s", vm_name, provider.key)
        vm.create_on_provider(allow_skip="default")
    else:
        logger.info("recycling deployed vm %s on provider %s", vm_name, provider.key)
    vm.provider.refresh_provider_relationships()
    return vm


def update_appliance(appliance):
    with appliance:
        red_hat_updates = RedHatUpdates(
            service="rhsm",
            url=conf.cfme_data["redhat_updates"]["registration"]["rhsm"]["url"],
            username=conf.credentials["rhsm"]["username"],
            password=conf.credentials["rhsm"]["password"],
            set_default_repository=True,
        )
        red_hat_updates.update_registration(validate=False)
        red_hat_updates.check_updates()
        wait_for(
            func=red_hat_updates.checked_updates,
            func_args=[appliance.server.name],
            delay=10,
            num_sec=600,
            fail_func=red_hat_updates.refresh,
        )
        if red_hat_updates.platform_updates_available():
            red_hat_updates.update_appliances()
        return appliance


def upgrade_appliances(appliances):
    for appliance in appliances:
        result = appliance.ssh_client.run_command("yum update -y", timeout=3600)
        assert result.success, "update failed {}".format(result.output)


def do_appliance_versions_match(appliance1, appliance2):
    """Checks if cfme-appliance has been updated by clearing the cache and checking the versions"""
    try:
        appliance2.rest_api._load_data()
    except Exception:
        logger.info("Couldn't reload the REST_API data - does server have REST?")
        pass
    try:
        del appliance2.version
        del appliance2.ssh_client.vmdb_version
    except AttributeError:
        logger.info(
            "Couldn't clear one or more cache - best guess it has already been cleared."
        )
    assert appliance1.version == appliance2.version
