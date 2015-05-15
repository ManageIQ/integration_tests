# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from utils.version import current_version

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.uncollectif(lambda: current_version() >= "5.3"),
]


@pytest.fixture(scope="module")
def backup_file_name():
    return "/tmp/ae_backup_{}.xml".format(fauxfactory.gen_alphanumeric(32))


@pytest.yield_fixture(scope="module")
def rake(ssh_client, backup_file_name):
    ssh_client.run_command("rm -f {}".format(backup_file_name))
    ssh_client.run_rake_command("evm:automate:backup FILE={}".format(backup_file_name))
    yield lambda command: ssh_client.run_rake_command(command)
    ssh_client.run_rake_command("evm:automate:clear")
    ssh_client.run_rake_command("evm:automate:restore FILE={}".format(backup_file_name))


def test_import_export_5_2(ssh_client, rake):
    # How does this test work?
    # 1. We pick a namespace and export it
    # 2. Then we drop whole AE domain
    # 3. We import the saved namespace from file
    # 4. We do AE backup and make diff with the exported namespace
    # If that returns $?==0, then it is all right
    ssh_client.run_command("rm -f /tmp/impexp_test_1.xml")
    ssh_client.run_command("rm -f /tmp/impexp_test_2.xml")
    # We pick namespace Automation
    rake("evm:automate:export NAMESPACE='Automation' FILE='/tmp/impexp_test_1.xml'")
    rake("evm:automate:clear")
    # Load it back up
    rake("evm:automate:import FILE='/tmp/impexp_test_1.xml'")
    # And do the backup
    rake("evm:automate:backup FILE='/tmp/impexp_test_2.xml'")
    # Check the difference
    rc = ssh_client.run_command("diff '/tmp/impexp_test_1.xml' '/tmp/impexp_test_2.xml'")[0]
    assert rc == 0, "Could not verify import/export functionality of the appliance"
