import pytest
from cfme.utils.conf import cfme_data

from cfme.configure.configuration.region_settings import RedHatUpdates
from cfme.fixtures.pytest_store import store
from cfme.test_framework.sprout.client import SproutClient, SproutException
from cfme.utils import conf
from cfme.utils.appliance import find_appliance
from cfme.utils.log import logger
from cfme.utils.version import Version
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod,
                            reason="pod appliance should be updated thru openshift mechanism")
]


def pytest_generate_tests(metafunc):
    """The following lines generate appliance versions based from the current build.
    Appliance version is split and minor_build is picked out for generating each version
    and appending it to the empty versions list"""
    versions = []
    version = find_appliance(metafunc).version

    split_ver = str(version).split(".")
    try:
        minor_build = split_ver[2]
        assert int(minor_build) != 0
    except IndexError:
        logger.exception('Caught IndexError generating for test_appliance_update, skipping')
    except AssertionError:
        logger.debug('Caught AssertionError: No previous z-stream version to update from')
        versions.append(pytest.param("bad:{!r}".format(version), marks=pytest.mark.uncollect(
            'Could not parse minor_build version from: {}'.format(version)
        )))
    else:
        for i in range(int(minor_build) - 1, -1, -1):
            versions.append("{}.{}.{}".format(split_ver[0], split_ver[1], i))
    metafunc.parametrize('old_version', versions, indirect=True)


@pytest.fixture
def old_version(request):
    return request.param


@pytest.fixture(scope="function", )
def appliance_preupdate(old_version, appliance):

    series = appliance.version.series()
    update_url = "update_url_{}".format(series.replace('.', ''))

    """Requests appliance from sprout based on old_versions, edits partitions and adds
    repo file for update"""

    usable = []
    sp = SproutClient.from_config()
    available_versions = set(sp.call_method('available_cfme_versions'))
    for a in available_versions:
        if a.startswith(old_version):
            usable.append(Version(a))
    usable.sort(reverse=True)
    try:
        apps, pool_id = sp.provision_appliances(count=1, preconfigured=True,
            lease_time=180, version=str(usable[0]))
    except Exception as e:
        logger.exception("Couldn't provision appliance with following error:{}".format(e))
        raise SproutException('No provision available')

    apps[0].db.extend_partition()
    urls = cfme_data["basic_info"][update_url]
    apps[0].ssh_client.run_command(
        "curl {} -o /etc/yum.repos.d/update.repo".format(urls)
    )
    logger.info('Appliance update.repo file: \n%s',
                apps[0].ssh_client.run_command('cat /etc/yum.repos.d/update.repo').output)
    yield apps[0]
    apps[0].ssh_client.close()
    sp.destroy_pool(pool_id)


@pytest.mark.rhel_testing
@pytest.mark.uncollectif(lambda: not store.current_appliance.is_downstream)
def test_update_yum(appliance_preupdate, appliance):
    """Tests appliance update between versions"""

    appliance_preupdate.evmserverd.stop()
    with appliance_preupdate.ssh_client as ssh:
        result = ssh.run_command('yum update -y', timeout=3600)
        assert result.success, "update failed {}".format(result.output)
    appliance_preupdate.evmserverd.start()
    appliance_preupdate.wait_for_web_ui()
    result = appliance_preupdate.ssh_client.run_command('cat /var/www/miq/vmdb/VERSION')
    assert result.output in appliance.version


@pytest.fixture(scope="function")
def enabled_embedded_appliance(appliance_preupdate):
    """Takes a preconfigured appliance and enables the embedded ansible role"""
    appliance_preupdate.enable_embedded_ansible_role()
    assert appliance_preupdate.is_embedded_ansible_running
    return appliance_preupdate


@pytest.fixture(scope="function")
def update_embedded_appliance(enabled_embedded_appliance, appliance):
    with enabled_embedded_appliance:
        red_hat_updates = RedHatUpdates(
            service='rhsm',
            url=conf.cfme_data['redhat_updates']['registration']['rhsm']['url'],
            username=conf.credentials['rhsm']['username'],
            password=conf.credentials['rhsm']['password'],
            set_default_repository=True
        )
        red_hat_updates.update_registration(validate=False)
        red_hat_updates.check_updates()
        wait_for(
            func=red_hat_updates.checked_updates,
            func_args=[appliance.server.name],
            delay=10,
            num_sec=100,
            fail_func=red_hat_updates.refresh
        )
        if red_hat_updates.platform_updates_available():
            red_hat_updates.update_appliances()
        return enabled_embedded_appliance


@pytest.mark.ignore_stream("upstream")
def test_embedded_ansible_update(update_embedded_appliance, appliance, old_version):
    """ Tests updating an appliance which has embedded ansible role enabled, also confirms that the
        role continues to function correctly after the update has completed"""
    def is_appliance_updated(appliance):
        """Checks if cfme-appliance has been updated"""
        result = update_embedded_appliance.ssh_client.run_command('cat /var/www/miq/vmdb/VERSION')
        assert result.output in appliance.version

    wait_for(is_appliance_updated, func_args=[update_embedded_appliance], num_sec=900)
    assert wait_for(func=lambda: update_embedded_appliance.is_embedded_ansible_running, num_sec=30)
    assert wait_for(func=lambda: update_embedded_appliance.is_rabbitmq_running, num_sec=30)
    assert wait_for(func=lambda: update_embedded_appliance.is_nginx_running, num_sec=30)
    assert update_embedded_appliance.ssh_client.run_command(
        'curl -kL https://localhost/ansibleapi | grep "AWX REST API"')
