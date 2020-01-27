import zlib
from collections import namedtuple
from configparser import ConfigParser
from contextlib import contextmanager
from io import StringIO
from re import escape as resc

import fauxfactory
import pytest
import requests
from lxml import etree

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
from cfme.utils.log_validator import LogValidator
from cfme.utils.providers import list_providers_by_class
from cfme.utils.ssh_expect import SSHExpect
from cfme.utils.version import Version
from cfme.utils.wait import wait_for


TimedCommand = namedtuple("TimedCommand", ["command", "timeout"])


@contextmanager
def waiting_for_ha_monitor_started(appl, standby_server_ip, timeout):
    if appl.version < '5.10':
        with LogValidator(
                "/var/www/miq/vmdb/config/failover_databases.yml",
                matched_patterns=[standby_server_ip],
                hostname=appl.hostname).waiting(timeout=timeout):
            yield
    else:
        yield
        wait_for(lambda: appl.evm_failover_monitor.running, timeout=300)


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
            for key, yaml in auth_data.auth_providers.items()
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


def get_puddle_cfme_version(repo_file_path):
    """ Gets the version of cfme package in the the [cfme] repo on repo_file_path """
    namespaces = {'repo': 'http://linux.duke.edu/metadata/repo',
                 'common': 'http://linux.duke.edu/metadata/common'}

    repofile = requests.get(repo_file_path).text
    cp = ConfigParser()
    cp.readfp(StringIO(repofile))

    cfme_baseurl = cp.get('cfme', 'baseurl')
    # The urljoin does replace the last bit of url when there is no slash on
    # the end, which does happen with the repos we get, therefore we better
    # join the urls just by string concatenation.
    repomd_url = '{}/repodata/repomd.xml'.format(cfme_baseurl)
    repomd_response = requests.get(repomd_url)
    assert repomd_response.ok
    repomd_root = etree.fromstring(repomd_response.content)
    cfme_primary_path, = repomd_root.xpath(
        "repo:data[@type='primary']/repo:location/@href",
        namespaces=namespaces)
    cfme_primary_url = '{}/{}'.format(cfme_baseurl, cfme_primary_path)
    cfme_primary_response = requests.get(cfme_primary_url)
    assert cfme_primary_response.ok
    primary_xml = zlib.decompress(cfme_primary_response.content, zlib.MAX_WBITS | 16)
    fl_root = etree.fromstring(primary_xml)
    repo_cfme_version, = fl_root.xpath(
        "common:package[common:name='cfme']/common:version/@ver",
        namespaces=namespaces)
    return repo_cfme_version


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
    picked_version = usable_sorted[-1]
    apps = []
    pool_id = None
    try:
        apps, pool_id = sp.provision_appliances(
            count=count,
            preconfigured=preconfigured,
            provider_type="rhevm",
            lease_time=180,
            version=str(picked_version),
        )
        url = cfme_data["basic_info"][update_url]
        assert get_puddle_cfme_version(url) == appliance.version
        for app in apps:
            app.db.extend_partition()
            app.ssh_client.run_command(
                "curl {} -o /etc/yum.repos.d/update.repo".format(url)
            )

        yield apps
    except AuthException:
        msg = ('Sprout credentials key or yaml maps missing or invalid,'
               'unable to provision appliance version {}'.format(picked_version))
        logger.exception(msg)
        pytest.skip(msg)
    finally:
        for app in apps:
            app.ssh_client.close()
        if pool_id:
            sp.destroy_pool(pool_id)


@pytest.fixture
def appliance_preupdate(appliance, old_version, request):
    """Requests single appliance from sprout."""
    with get_apps(appliance, old_version, count=1, preconfigured=True,
                  pytest_config=request.config) as apps:
        yield apps[0]


@pytest.fixture
def multiple_preupdate_appliances(appliance, old_version, request):
    """Requests multiple appliances from sprout."""
    with get_apps(appliance, old_version, count=2, preconfigured=False,
                  pytest_config=request.config) as apps:
        yield apps


@pytest.fixture
def ha_multiple_preupdate_appliances(appliance, old_version, request):
    """Requests multiple appliances from sprout."""
    with get_apps(appliance, old_version, count=3, preconfigured=False,
                  pytest_config=request.config) as apps:
        yield apps


def configure_appliances_ha(appliances, pwd):
    """Configure HA environment

    Appliance one configuring dedicated database, 'ap' launch appliance_console,
    '' clear info screen, '5' setup db, '1' Creates v2_key, '1' selects internal db,
    '1' use partition, 'y' create dedicated db, 'pwd' db password, 'pwd' confirm db password + wait
    and '' finish.

    Appliance two creating region in dedicated database, 'ap' launch appliance_console, '' clear
    info screen, '5' setup db, '2' fetch v2_key, 'app0_ip' appliance ip address, '' default user,
    'pwd' appliance password, '' default v2_key location, '2' create region in external db, '0' db
    region number, 'y' confirm create region in external db 'app0_ip', '' ip and default port for
    dedicated db, '' use default db name, '' default username, 'pwd' db password, 'pwd' confirm db
    password + wait and '' finish.

    Appliance one configuring primary node for replication, 'ap' launch appliance_console, '' clear
    info screen, '6' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait to configure, '' finish.


    Appliance three configuring standby node for replication, 'ap' launch appliance_console, ''
    clear info screen, '6' configure db replication, '2' configure node as standby, '2' cluster node
    number set to 2, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, app1_ip standby appliance ip, confirm settings and wait
    to configure finish, '' finish.


    Appliance two configuring automatic failover of database nodes, 'ap' launch appliance_console,
    '' clear info screen '9' configure application database failover monitor, '1' start failover
    monitor. wait 30 seconds for service to start '' finish.

    """
    apps0, apps1, apps2 = appliances
    app0_ip = apps0.hostname

    # Configure first appliance as dedicated database
    with SSHExpect(apps0) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        interaction.answer('Choose the advanced setting: ',
                           '5' if apps0.version < '5.10' else '7')  # Configure Database
        interaction.answer(resc('Choose the encryption key: |1| '), '1')
        interaction.answer('Choose the database operation: ', '1')
        # On 5.10, rhevm provider:
        #
        #    database disk
        #
        #    1) /dev/sr0: 0 MB
        #    2) /dev/vdb: 4768 MB
        #    3) Don't partition the disk
        interaction.answer(resc('Choose the database disk: '),
                          '1' if apps0.version < '5.10' else '2')
        # Should this appliance run as a standalone database server?
        interaction.answer(resc('? (Y/N): |N| '), 'y')
        interaction.answer('Enter the database password on localhost: ', pwd)
        interaction.answer('Enter the database password again: ', pwd)
        # Configuration activated successfully.
        interaction.answer('Press any key to continue.', '', timeout=6 * 60)

        wait_for(lambda: apps0.db.is_dedicated_active, num_sec=4 * 60)

    # Configure EVM webui appliance with create region in dedicated database
    with SSHExpect(apps2) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        interaction.answer('Choose the advanced setting: ',
                           '5' if apps2.version < '5.10' else '7')  # Configure Database
        interaction.answer(resc('Choose the encryption key: |1| '), '2')
        interaction.send(app0_ip)
        interaction.answer(resc('Enter the appliance SSH login: |root| '), '')
        interaction.answer('Enter the appliance SSH password: ', pwd)
        interaction.answer(
            resc('Enter the path of remote encryption key: |/var/www/miq/vmdb/certs/v2_key| '),
            '')
        interaction.answer('Choose the database operation: ', '2', timeout=30)
        interaction.answer('Enter the database region number: ', '0')
        # WARNING: Creating a database region will destroy any existing data and
        # cannot be undone.
        interaction.answer(resc('Are you sure you want to continue? (Y/N):'), 'y')
        interaction.answer('Enter the database hostname or IP address: ', app0_ip)
        interaction.answer(resc('Enter the port number: |5432| '), '')
        interaction.answer(r'Enter the name of the database on .*: \|vmdb_production\| ', '')
        interaction.answer(resc('Enter the username: |root| '), '')
        interaction.answer('Enter the database password on .*: ', pwd)
        # Configuration activated successfully.
        interaction.answer('Press any key to continue.', '', timeout=360)

    apps2.evmserverd.wait_for_running()
    apps2.wait_for_web_ui()

    configure_primary_replication_node(apps0, pwd)
    configure_standby_replication_node(apps1, pwd, app0_ip)

    configure_automatic_failover(apps2, primary_ip=None)

    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, apps2).setup()
    provider_app_crud(EC2Provider, apps2).setup()
    return appliances


def answer_cluster_related_questions(interaction, node_uid, db_name,
        db_username, db_password):
    # It seems like sometimes, the word "Enter " ... dosen't fit to the paramiko-expect buffer.
    # This seems to happen when (re)configuring the standby replication node.
    interaction.answer('.* the number uniquely identifying '
                       'this node in the replication cluster: ', node_uid)
    interaction.answer(resc('Enter the cluster database name: |vmdb_production| '), db_name)
    interaction.answer(resc('Enter the cluster database username: |root| '), db_username)
    interaction.answer('Enter the cluster database password: ', db_password)
    interaction.answer('Enter the cluster database password: ', db_password)


def configure_primary_replication_node(appl, pwd):
    # Configure primary replication node
    with SSHExpect(appl) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        # 6/8 for Configure Database Replication
        interaction.answer('Choose the advanced setting: ',
                           '6' if appl.version < '5.10' else '8')
        interaction.answer('Choose the database replication operation: ', '1')
        answer_cluster_related_questions(interaction, node_uid='1',
            db_name='', db_username='', db_password=pwd)
        interaction.answer(r'Enter the primary database hostname or IP address: \|.*\| ',
                        appl.hostname)
        interaction.answer(resc('Apply this Replication Server Configuration? (Y/N): '), 'y')
        interaction.answer('Press any key to continue.', '')


def reconfigure_primary_replication_node(appl, pwd):
    # Configure primary replication node
    with SSHExpect(appl) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        interaction.answer('Choose the advanced setting: ',
                           '6' if appl.version < '5.10' else '8')
        # 6/8 for Configure Database Replication

        interaction.answer('Choose the database replication operation: ', '1')
        answer_cluster_related_questions(interaction, node_uid='1',
            db_name='', db_username='', db_password=pwd)
        interaction.answer(r'Enter the primary database hostname or IP address: \|.*\| ',
                           appl.hostname)
        # Warning: File /etc/repmgr.conf exists. Replication is already configured
        interaction.answer(resc('Continue with configuration? (Y/N): '), 'y')
        interaction.answer(resc('Apply this Replication Server Configuration? (Y/N): '), 'y')
        interaction.answer('Press any key to continue.', '')


def configure_standby_replication_node(appl, pwd, primary_ip):
    # Configure secondary (standby) replication node
    with SSHExpect(appl) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        interaction.answer('Choose the advanced setting: ',
                           '6' if appl.version < '5.10' else '8')
        # 6/8 for Configure Database Replication

        # Configure Server as Standby
        interaction.answer('Choose the database replication operation: ', '2')
        interaction.answer(resc('Choose the encryption key: |1| '), '2')
        interaction.send(primary_ip)
        interaction.answer(resc('Enter the appliance SSH login: |root| '), '')
        interaction.answer('Enter the appliance SSH password: ', pwd)
        interaction.answer(resc('Enter the path of remote encryption key: '
                                '|/var/www/miq/vmdb/certs/v2_key| '), '')
        interaction.answer(resc('Choose the standby database disk: '),
                           '1' if appl.version < '5.10' else '2')
        answer_cluster_related_questions(interaction, node_uid='2',
            db_name='', db_username='', db_password=pwd)
        interaction.answer('Enter the primary database hostname or IP address: ', primary_ip)
        interaction.answer(r'Enter the Standby Server hostname or IP address: \|.*\| ',
                           appl.hostname)
        interaction.answer(resc('Configure Replication Manager (repmgrd) for automatic '
                                r'failover? (Y/N): '), 'y')
        interaction.answer(resc('Apply this Replication Server Configuration? (Y/N): '), 'y')
        interaction.answer('Press any key to continue.', '', timeout=10 * 60)


def reconfigure_standby_replication_node(appl, pwd, primary_ip, repmgr_reconfigure=False):
    # Configure secondary (standby) replication node
    with SSHExpect(appl) as interaction:
        interaction.send('ap')
        # When reconfiguring, the ap command may hang for 60s even.
        interaction.answer('Press any key to continue.', '', timeout=120)
        interaction.answer('Choose the advanced setting: ',
                           '6' if appl.version < '5.10' else '8')
        # 6/8 for Configure Database Replication

        # Configure Server as Standby
        interaction.answer('Choose the database replication operation: ', '2')
        # Would you like to remove the existing database before configuring as a standby server?
        # WARNING: This is destructive. This will remove all previous data from this server
        interaction.answer(resc('Continue? (Y/N): '), 'y')
        interaction.answer(
            # Don't partition the disk
            resc('Choose the standby database disk: |1| '),
            '1' if appl.version < '5.10' else '2')
        interaction.answer(resc(
            "Are you sure you don't want to partition the Standby "
            "database disk? (Y/N): "), 'y')
        answer_cluster_related_questions(interaction, node_uid='2',
            db_name='', db_username='', db_password=pwd)
        interaction.answer('Enter the primary database hostname or IP address: ', primary_ip)
        interaction.answer(r'Enter the Standby Server hostname or IP address: \|.*\| ', '')
        interaction.answer(resc(
            'Configure Replication Manager (repmgrd) for automatic '
            r'failover? (Y/N): '), 'y')
        # interaction.answer('An active standby node (10.8.198.223) with the node number 2
        # already exists\n')
        # 'Would you like to continue configuration by overwriting '
        # 'the existing node?
        interaction.answer(resc('(Y/N): |N| '), 'y')
        # Warning: File /etc/repmgr.conf exists. Replication is already configured
        interaction.answer(resc('Continue with configuration? (Y/N): '), 'y')
        interaction.answer(resc('Apply this Replication Server Configuration? (Y/N): '), 'y')
        interaction.answer('Press any key to continue.', '', timeout=20)


def configure_automatic_failover(appl, primary_ip):
    # Configure automatic failover on EVM appliance
    with SSHExpect(appl) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        interaction.expect('Choose the advanced setting: ')

        with waiting_for_ha_monitor_started(appl, primary_ip, timeout=300):
            # Configure Application Database Failover Monitor
            interaction.send('8' if appl.version < '5.10' else '10')
            interaction.answer('Choose the failover monitor configuration: ', '1')
            # Failover Monitor Service configured successfully
            interaction.answer('Press any key to continue.', '')


@pytest.fixture
def ha_appliances_with_providers(ha_multiple_preupdate_appliances, app_creds):
    configure_appliances_ha(ha_multiple_preupdate_appliances, app_creds["password"])
    return ha_multiple_preupdate_appliances


def replicated_appliances_with_providers(multiple_preupdate_appliances):
    """Returns two database-owning appliances, configures with providers."""
    appl1, appl2 = multiple_preupdate_appliances
    # configure appliances
    appl1.configure(region=0)
    appl1.wait_for_web_ui()
    appl2.configure(region=99, key_address=appl1.hostname)
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
    vm_name = fauxfactory.gen_alphanumeric(18, start="test_rest_db_")
    coll = provider.appliance.provider_based_collection(provider, coll_type="vms")
    vm = coll.instantiate(vm_name, provider)
    if not provider.mgmt.does_vm_exist(vm_name):
        logger.info("deploying %s on provider %s", vm_name, provider.key)
        vm.create_on_provider(allow_skip="default")
        request.addfinalizer(vm.delete)
    else:
        logger.info("recycling deployed vm %s on provider %s", vm_name, provider.key)
    vm.provider.refresh_provider_relationships()
    return vm


def update_appliance(appliance):
    appliance.browser_steal = True
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
