import tempfile

import pytest

from cfme.test_framework.sprout.client import SproutClient, SproutException
from scripts.repo_gen import process_url, build_file
from utils.version import Version
from utils.appliance import current_appliance
from utils.log import logger
from utils.conf import cfme_data
from utils.version import get_stream
from utils import os

versions = []


@pytest.yield_fixture(scope="function")
def appliance_preupdate(old_version):

    """The following lines generate appliance versions based from the current build.
    Appliance version is split and minor_build is picked out for generating each version
    and appending it to the empty versions list"""

    version = current_appliance.version
    split_ver = str(version).split(".")
    minor_build = split_ver[2]

    for i in range(int(minor_build) - 1, -1, -1):
        versions.append("{}.{}.{}".format(split_ver[0], split_ver[1], i))

    update_url = ('update_url_' + ''.join([i for i in get_stream(current_appliance.version)
        if i.isdigit()]))

    """Requests appliance from sprout based on old_versions, edits partitions and adds
    repo file for update"""

    usable = []
    sp = SproutClient.from_config()
    available_versions = set(sp.call_method('available_cfme_versions'))
    for ver in versions:
        for a in available_versions:
            if a.startswith(ver):
                usable.append(a)
    usable = sorted([Version(i) for i in usable], reverse=True)
    try:
        apps, pool_id = sp.provision_appliances(count=1, preconfigured=True,
            lease_time=180, version=str(usable[0]))
    except Exception as e:
        logger.warning("Couldn't provision appliance with following error:")
        logger.warning("{}".format(e))
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
def test_update_yum(appliance_preupdate, appliance):

    # Tests appliance update between versions

    appliance_preupdate.evmserverd.stop()
    with appliance_preupdate.ssh_client as ssh:
        rc, out = ssh.run_command('yum update -y', timeout=3600)
        assert rc == 0, "update failed {}".format(out)
    appliance_preupdate.evmserverd.start()
    assert appliance.version == appliance_preupdate.version
