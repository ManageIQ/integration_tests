import zlib
from collections import namedtuple
from configparser import ConfigParser
from contextlib import contextmanager
from io import StringIO

import fauxfactory
import pytest
import requests
from lxml import etree

import cfme.utils.auth as authutil
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.configure.configuration.region_settings import RedHatUpdates
from cfme.fixtures.appliance import _collect_logs
from cfme.fixtures.appliance import sprout_appliances
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.test_framework.sprout.client import AuthException
from cfme.test_framework.sprout.client import SproutClient
from cfme.utils import conf
from cfme.utils.appliance.console import configure_appliances_ha
from cfme.utils.conf import auth_data
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.providers import list_providers_by_class
from cfme.utils.version import Version
from cfme.utils.wait import wait_for

TimedCommand = namedtuple("TimedCommand", ["command", "timeout"])


@pytest.fixture()
def unconfigured_appliance(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]
        _collect_logs(request.config, apps)


@pytest.fixture()
def unconfigured_appliance_secondary(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]
        _collect_logs(request.config, apps)


@pytest.fixture()
def unconfigured_appliances(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=3,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps
        _collect_logs(request.config, apps)


@pytest.fixture()
def configured_appliance(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=True,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]
        _collect_logs(request.config, apps)


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
    menu = "5" if app.version > 5.11 else "7"
    partition = "2" if unconfigured_appliance.version < "5.11" else "1"
    command_set = ("ap", "", menu, "1", "1", partition, "y", pwd, TimedCommand(pwd, 360), "")
    app.appliance_console.run_commands(command_set, timeout=20)
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
    repomd_url = f'{cfme_baseurl}/repodata/repomd.xml'
    repomd_response = requests.get(repomd_url)
    assert repomd_response.ok
    repomd_root = etree.fromstring(repomd_response.content)
    cfme_primary_path, = repomd_root.xpath(
        "repo:data[@type='primary']/repo:location/@href",
        namespaces=namespaces)
    cfme_primary_url = f'{cfme_baseurl}/{cfme_primary_path}'
    cfme_primary_response = requests.get(cfme_primary_url)
    assert cfme_primary_response.ok
    primary_xml = zlib.decompress(cfme_primary_response.content, zlib.MAX_WBITS | 16)
    fl_root = etree.fromstring(primary_xml)
    repo_cfme_version, = fl_root.xpath(
        "common:package[common:name='cfme']/common:version/@ver",
        namespaces=namespaces)
    return repo_cfme_version


@contextmanager
def get_apps(requests, appliance, old_version, count, preconfigured, pytest_config):
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
                f"curl {url} -o /etc/yum.repos.d/update.repo"
            )

        yield apps
    except AuthException:
        msg = ('Sprout credentials key or yaml maps missing or invalid,'
               'unable to provision appliance version {}'.format(picked_version))
        logger.exception(msg)
        pytest.skip(msg)
    finally:
        _collect_logs(pytest_config, apps)
        for app in apps:
            app.ssh_client.close()
        if pool_id:
            sp.destroy_pool(pool_id)


@pytest.fixture
def appliance_preupdate(appliance, old_version, request):
    """Requests single appliance from sprout."""
    with get_apps(request, appliance, old_version, count=1, preconfigured=True,
                  pytest_config=request.config) as apps:
        yield apps[0]


@pytest.fixture
def multiple_preupdate_appliances(appliance, old_version, request):
    """Requests multiple appliances from sprout."""
    with get_apps(request, appliance, old_version, count=2, preconfigured=False,
                  pytest_config=request.config) as apps:
        yield apps


@pytest.fixture
def ha_multiple_preupdate_appliances(appliance, old_version, request):
    """Requests multiple appliances from sprout."""
    with get_apps(request, appliance, old_version, count=3, preconfigured=False,
                  pytest_config=request.config) as apps:
        yield apps


@pytest.fixture
def ha_appliances_with_providers(ha_multiple_preupdate_appliances, app_creds):
    _, _, appl2 = configure_appliances_ha(ha_multiple_preupdate_appliances, app_creds["password"])
    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl2).setup()
    provider_app_crud(OpenStackProvider, appl2).setup()
    return ha_multiple_preupdate_appliances


@pytest.fixture
def distributed_appliances(temp_appliance_preconfig_funcscope_rhevm,
        temp_appliance_unconfig_funcscope_rhevm):
    """Configure one database-owning appliance, and a second appliance
       that connects to the database of the first.
    """
    primary_appliance = temp_appliance_preconfig_funcscope_rhevm
    secondary_appliance = temp_appliance_unconfig_funcscope_rhevm
    secondary_appliance.configure(region=0, key_address=primary_appliance.hostname,
        db_address=primary_appliance.hostname)

    primary_appliance.browser_steal = True
    secondary_appliance.browser_steal = True

    return primary_appliance, secondary_appliance


@pytest.fixture
def replicated_appliances(temp_appliance_preconfig_funcscope_rhevm,
        temp_appliance_unconfig_funcscope_rhevm):
    """Configure a global appliance with region 99, sharing the same encryption key as the
    preconfigured remote appliance with region 0. Then set up database replication between them.
    """
    remote_appliance = temp_appliance_preconfig_funcscope_rhevm
    global_appliance = temp_appliance_unconfig_funcscope_rhevm

    logger.info("Starting appliance replication configuration.")
    global_appliance.configure(region=99, key_address=remote_appliance.hostname)

    remote_appliance.set_pglogical_replication(replication_type=':remote')
    global_appliance.set_pglogical_replication(replication_type=':global')
    global_appliance.add_pglogical_replication_subscription(remote_appliance.hostname)
    logger.info("Finished appliance replication configuration.")

    remote_appliance.browser_steal = True
    global_appliance.browser_steal = True

    return remote_appliance, global_appliance


@pytest.fixture
def replicated_appliances_preupdate(multiple_preupdate_appliances):
    """Configure a remote appliance with region 0 and a global appliance with region 99, sharing
    the same encryption key. Then set up database replication between them.
    """
    remote_appliance, global_appliance = multiple_preupdate_appliances

    logger.info("Starting appliance replication configuration.")
    remote_appliance.configure(region=0)
    global_appliance.configure(region=99, key_address=remote_appliance.hostname)

    remote_appliance.set_pglogical_replication(replication_type=':remote')
    global_appliance.set_pglogical_replication(replication_type=':global')
    global_appliance.add_pglogical_replication_subscription(remote_appliance.hostname)
    logger.info("Finished appliance replication configuration.")

    global_appliance.browser_steal = True
    remote_appliance.browser_steal = True

    return remote_appliance, global_appliance


@pytest.fixture
def replicated_appliances_with_providers(replicated_appliances):
    """Add two providers to the remote appliance."""
    remote_appliance, global_appliance = replicated_appliances
    provider_app_crud(VMwareProvider, remote_appliance).setup()
    provider_app_crud(OpenStackProvider, remote_appliance).setup()
    return remote_appliance, global_appliance


@pytest.fixture
def replicated_appliances_preupdate_with_providers(replicated_appliances_preupdate):
    """Add two providers to the remote appliance."""
    remote_appliance, global_appliance = replicated_appliances_preupdate
    provider_app_crud(VMwareProvider, remote_appliance).setup()
    provider_app_crud(OpenStackProvider, remote_appliance).setup()
    return remote_appliance, global_appliance


@pytest.fixture
def ext_appliances_with_providers(multiple_preupdate_appliances, app_creds_modscope):
    """Returns two database-owning appliances, configures first appliance with providers."""
    appl1, appl2 = multiple_preupdate_appliances
    app_ip = appl1.hostname
    # configure appliances
    appl1.configure(region=0)
    appl1.wait_for_miq_ready()
    appl2.appliance_console_cli.configure_appliance_external_join(
        app_ip,
        app_creds_modscope["username"],
        app_creds_modscope["password"],
        "vmdb_production",
        app_ip,
        app_creds_modscope["sshlogin"],
        app_creds_modscope["sshpass"],
    )
    appl2.wait_for_miq_ready()
    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(OpenStackProvider, appl1).setup()
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
    provider_app_crud(OpenStackProvider, appl1).setup()
    return appliance_preupdate


def provider_app_crud(provider_class, appliance):
    try:
        prov = list_providers_by_class(provider_class)[0]
        logger.info(f"using provider {prov.name}")
        prov.appliance = appliance
        return prov
    except IndexError:
        pytest.skip(f"No {provider_class.type_name} providers available (required)")


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
        assert result.success, f"update failed {result.output}"


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
