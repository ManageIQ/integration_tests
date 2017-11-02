import tempfile
import pytest

from cfme.test_framework.sprout.client import SproutClient, SproutException
from fixtures.pytest_store import store
from scripts.repo_gen import process_url, build_file
from cfme.configure.configuration.region_settings import RedHatUpdates
from cfme.utils.wait import wait_for
from cfme.utils.version import Version, current_version
from cfme.utils.log import logger
from cfme.utils import conf
from cfme.utils import os
from cfme.utils.appliance import get_or_create_current_appliance


def pytest_generate_tests(metafunc):
    """The following lines generate appliance versions based from the current build.
    Appliance version is split and minor_build is picked out for generating each version
    and appending it to the empty versions list"""
    versions = []
    version = get_or_create_current_appliance().version

    split_ver = str(version).split(".")
    try:
        minor_build = split_ver[2]
        assert int(minor_build) != 0
    except IndexError:
        logger.exception('Caught IndexError generating for test_appliance_update, skipping')
    except AssertionError:
        logger.exception('Caught AssertionError: No previous z-stream version to update from')
        versions.append(pytest.param("bad:{!r}".format(version), marks=pytest.mark.skip(
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
    urls = process_url(conf.cfme_data['basic_info'][update_url])
    output = build_file(urls)
    with tempfile.NamedTemporaryFile('w') as f:
        f.write(output)
        f.flush()
        os.fsync(f.fileno())
        apps[0].ssh_client.put_file(
            f.name, '/etc/yum.repos.d/update.repo')
    yield apps[0]
    apps[0].ssh_client.close()
    sp.destroy_pool(pool_id)


@pytest.mark.uncollectif(lambda: not store.current_appliance.is_downstream)
def test_update_yum(appliance_preupdate, appliance):
    """Tests appliance update between versions"""

    appliance_preupdate.evmserverd.stop()
    with appliance_preupdate.ssh_client as ssh:
        rc, out = ssh.run_command('yum update -y', timeout=3600)
        assert rc == 0, "update failed {}".format(out)
    appliance_preupdate.evmserverd.start()
    appliance_preupdate.wait_for_web_ui()
    assert appliance.version == appliance_preupdate.version


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
@pytest.mark.uncollectif(lambda: current_version() < "5.8")
def test_embedded_ansible_update(update_embedded_appliance, appliance, old_version):
    """ Tests updating an appliance which has embedded ansible role enabled, also confirms that the
        role continues to function correctly after the update has completed"""
    def is_appliance_updated(appliance):
        """Checks if cfme-appliance has been updated"""
        assert appliance.version == update_embedded_appliance.version

    wait_for(is_appliance_updated, func_args=[update_embedded_appliance], num_sec=900)
    assert wait_for(func=lambda: update_embedded_appliance.is_embedded_ansible_running, num_sec=30)
    assert wait_for(func=lambda: update_embedded_appliance.is_rabbitmq_running, num_sec=30)
    assert wait_for(func=lambda: update_embedded_appliance.is_nginx_running, num_sec=30)
    assert update_embedded_appliance.ssh_client.run_command(
        'curl -kL https://localhost/ansibleapi | grep "Ansible Tower REST API"')
