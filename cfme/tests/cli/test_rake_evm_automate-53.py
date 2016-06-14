# -*- coding: utf-8 -*-
"""This module contains tests that are supposed to test CFME's CLI functionality."""
import pytest

from cfme.automate.explorer import Domain
from utils.path import data_path
from utils.update import update

cli_path = data_path.join("cli")


@pytest.yield_fixture(scope="function")
def rake(ssh_client):
    ssh_client.run_rake_command("evm:automate:clear")
    ssh_client.run_rake_command("evm:automate:reset")
    yield lambda command: ssh_client.run_rake_command(command)
    # A bit slower but it will at least make it reliable
    ssh_client.run_rake_command("evm:automate:clear")
    ssh_client.run_rake_command("evm:automate:reset")


@pytest.fixture(scope="function")
def qe_ae_data(ssh_client, rake):
    ssh_client.put_file(cli_path.join("QECliTesting.yaml").strpath, "/root/QECliTesting.yaml")
    rc, stdout = rake(
        "evm:automate:import DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml PREVIEW=false "
        "ENABLED=true SYSTEM=false")
    assert rc == 0, stdout
    # Now we have to enable the domain to make it work.
    qe_cli_testing = Domain(name="QECliTesting")
    if not qe_cli_testing.is_enabled:
        with update(qe_cli_testing):
            qe_cli_testing.enabled = True


@pytest.mark.tier(1)
@pytest.mark.smoke
def test_evm_automate_import_export_works_upstream(ssh_client, rake, soft_assert):
    """This test checks whether CLI import and export works.

    Prerequisities:
        * ``data/cli/QECliTesting.yaml`` file

    Steps:
        * Upload the ``QECliTesting.yaml`` file to an appliance
        * Use ``evm:automate:import`` rake task to import the testing file.
        * Use ``evm:automate:export`` rake task to export the data to another file.
        * Verify the file exists.
    """
    ssh_client.put_file(cli_path.join("QECliTesting.yaml").strpath, "/root/QECliTesting.yaml")
    rc, stdout = rake(
        "evm:automate:import DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml PREVIEW=false "
        "SYSTEM=false")
    assert rc == 0, stdout
    ssh_client.run_command("rm -f QECliTesting.yaml")
    rc, stdout = rake("evm:automate:export DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml")
    assert rc == 0, stdout
    assert ssh_client.run_command("ls /root/QECliTesting.yaml")[0] == 0, "Could not verify export!"


@pytest.mark.tier(3)
def test_evm_automate_simulate_upstream(rake, qe_ae_data, ssh_client):
    """This test checks whether CLI simulation works.

    Prerequisities:
        * ``data/cli/QECliTesting.yaml`` file imported

    Steps:
        * Run ``evm:automate:simulate DOMAIN=QECliTesting NAMESPACE=System CLASS=Request
            INSTANCE=touch`` rake task
        * Verify the file ``/var/www/miq/vmdb/check_file`` exists and it contains string
            ``check content``
    """
    ssh_client.run_command("rm -f /var/www/miq/vmdb/check_file")
    rc, stdout = rake(
        "evm:automate:simulate DOMAIN=QECliTesting NAMESPACE=System CLASS=Request INSTANCE=touch")
    assert rc == 0, stdout
    rc, stdout = ssh_client.run_command("cat /var/www/miq/vmdb/check_file")
    assert rc == 0, "Could not find the file created by AE policy"
    assert stdout.strip() == "check content", "The file has wrong contents"


@pytest.mark.tier(1)
@pytest.mark.smoke
def test_evm_automate_convert(request, rake, ssh_client):
    """This test checks whether conversion from older XML format works.

    Prerequisities:
        * ``data/qe_event_handler.xml`` file.

    Steps:
        * Upload the testing file to the appliance.
        * Convert the file to ZIP using ``evm:automate:convert`` rake task
        * Import the ZIP file using ``evm:automate_import`` rake task.
        * Use ``evm:automate:extract_methods FOLDER=/some_folder`` and verify that a file named
            ``relay_events.rb`` is present in the directory hierarchy.
    """
    ssh_client.put_file(data_path.join("qe_event_handler.xml").strpath, "/root/convert_test.xml")
    request.addfinalizer(lambda: ssh_client.run_command("rm -f /root/convert_test.xml"))
    rc, stdout = rake(
        "evm:automate:convert DOMAIN=Default FILE=/root/convert_test.xml "
        "ZIP_FILE=/root/convert_test.zip")
    request.addfinalizer(lambda: ssh_client.run_command("rm -f /root/convert_test.zip"))
    assert rc == 0, stdout
    rc, stdout = ssh_client.run_command("ls -l /root/convert_test.zip")
    assert rc == 0, stdout
    rc, stdout = rake(
        "evm:automate:import ZIP_FILE=/root/convert_test.zip DOMAIN=Default OVERWRITE=true "
        "PREVIEW=false SYSTEM=false")
    assert rc == 0, stdout
    # Extract the methods so we can see if it was imported
    rc, stdout = rake("evm:automate:extract_methods FOLDER=/root/automate_methods")
    request.addfinalizer(lambda: ssh_client.run_command("rm -rf /root/automate_methods"))
    assert rc == 0, stdout
    rc, stdout = ssh_client.run_command("find /root/automate_methods | grep 'relay_events[.]rb$'")
    assert rc == 0, "Could not find the method in the extracted methods directory"
