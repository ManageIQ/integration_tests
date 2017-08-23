# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.utils.version import current_version

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.uncollectif(lambda: current_version() >= "5.3"),
]


@pytest.fixture(scope="module")
def backup_file_name():
    return "/tmp/ae_backup_{}.xml".format(fauxfactory.gen_alphanumeric(32))


@pytest.yield_fixture(scope="module")
def rake(appliance, backup_file_name):
    appliance.ssh_client.run_command("rm -f {}".format(backup_file_name))
    appliance.ssh_client.run_rake_command("evm:automate:backup FILE={}".format(backup_file_name))
    yield lambda command: appliance.ssh_client.run_rake_command(command)
    appliance.ssh_client.run_rake_command("evm:automate:clear")
    appliance.ssh_client.run_rake_command("evm:automate:restore FILE={}".format(backup_file_name))


def test_import_export_5_2(appliance, rake):
    """Test that import and export work for Control.

    Steps:
        * Pick a namespace and export it using ``evm:automate:export`` rake task
        * Then drop whole AE domain using ``evm:automate:clear`` rake task
        * Import the saved namespace from file using ``evm:automate:import`` rake task
        * Do AE backup and make ``diff`` with the exported namespace
        * If ``diff`` returns $?==0, then it is all right
    """
    # How does this test work?
    appliance.ssh_client.run_command("rm -f /tmp/impexp_test_1.xml")
    appliance.ssh_client.run_command("rm -f /tmp/impexp_test_2.xml")
    # We pick namespace Automation
    rake("evm:automate:export NAMESPACE='Automation' FILE='/tmp/impexp_test_1.xml'")
    rake("evm:automate:clear")
    # Load it back up
    rake("evm:automate:import FILE='/tmp/impexp_test_1.xml'")
    # And do the backup
    rake("evm:automate:backup FILE='/tmp/impexp_test_2.xml'")
    # Check the difference
    rc = appliance.ssh_client.run_command(
        "diff '/tmp/impexp_test_1.xml' '/tmp/impexp_test_2.xml'")[0]
    assert rc == 0, "Could not verify import/export functionality of the appliance"
