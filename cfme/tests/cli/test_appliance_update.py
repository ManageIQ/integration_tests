import tempfile
import pytest

from cfme.test_framework.sprout.client import SproutClient, SproutException
from scripts.repo_gen import process_url, build_file
from utils.version import Version
from utils.log import logger
from utils.conf import cfme_data
from utils.appliance import current_appliance
from utils import os

versions = []


def pytest_generate_tests(metafunc):
    """The following lines generate appliance versions based from the current build.
    Appliance version is split and minor_build is picked out for generating each version
    and appending it to the empty versions list"""

    version = current_appliance.version
    split_ver = str(version).split(".")
    try:
        minor_build = split_ver[2]
    except IndexError:
        logger.exception('Caught IndexError generating for test_appliance_update, skipping')
        pytest.skip('Could not parse minor_build version from: {}'.format(version))

    for i in range(int(minor_build) - 1, -1, -1):
        versions.append("{}.{}.{}".format(split_ver[0], split_ver[1], i))


@pytest.yield_fixture(scope="function")
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
    urls = process_url(cfme_data['basic_info'][update_url])
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


@pytest.mark.parametrize('old_version', versions)
@pytest.mark.uncollectif(lambda appliance: not appliance.is_downstream)
def test_update_yum(appliance_preupdate, appliance):

    """Tests appliance update between versions"""

    appliance_preupdate.evmserverd.stop()
    with appliance_preupdate.ssh_client as ssh:
        rc, out = ssh.run_command('yum update -y', timeout=3600)
        assert rc == 0, "update failed {}".format(out)
    appliance_preupdate.evmserverd.start()
    assert appliance.version == appliance_preupdate.version
