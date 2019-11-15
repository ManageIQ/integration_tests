"""This module contains tests that are supposed to test CFME's CLI functionality."""
import pytest

from cfme.automate.explorer.domain import DomainCollection
from cfme.utils.path import data_path
from cfme.utils.update import update

cli_path = data_path.join("cli")


@pytest.fixture(scope="function")
def rake(appliance):
    appliance.ssh_client.run_rake_command("evm:automate:clear")
    appliance.ssh_client.run_rake_command("evm:automate:reset")
    yield lambda command: appliance.ssh_client.run_rake_command(command)
    # A bit slower but it will at least make it reliable
    appliance.ssh_client.run_rake_command("evm:automate:clear")
    appliance.ssh_client.run_rake_command("evm:automate:reset")


@pytest.fixture(scope="function")
def qe_ae_data(request, appliance, rake):
    appliance.ssh_client.put_file(
        cli_path.join("QECliTesting.yaml").strpath, "/root/QECliTesting.yaml")
    result = rake(
        "evm:automate:import DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml PREVIEW=false "
        "ENABLED=true SYSTEM=false")
    assert result.success, result.output
    # Now we have to enable the domain to make it work.
    qe_cli_testing = DomainCollection(appliance).instantiate(name='QECliTesting')
    request.addfinalizer(qe_cli_testing.delete_if_exists)
    if not qe_cli_testing.enabled:
        with update(qe_cli_testing):
            qe_cli_testing.enabled = True


@pytest.mark.tier(1)
@pytest.mark.smoke
def test_evm_automate_import_export_works_upstream(appliance, rake, soft_assert):
    """This test checks whether CLI import and export works.

    Prerequisities:
        * ``data/cli/QECliTesting.yaml`` file

    Steps:
        * Upload the ``QECliTesting.yaml`` file to an appliance
        * Use ``evm:automate:import`` rake task to import the testing file.
        * Use ``evm:automate:export`` rake task to export the data to another file.
        * Verify the file exists.

    Polarion:
        assignee: sbulage
        casecomponent: Automate
        initialEstimate: 1/3h
    """
    appliance.ssh_client.put_file(
        cli_path.join("QECliTesting.yaml").strpath, "/root/QECliTesting.yaml")
    result = rake(
        "evm:automate:import DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml PREVIEW=false "
        "SYSTEM=false")
    assert result.success, result.output
    appliance.ssh_client.run_command("rm -f /root/QECliTesting.yaml")
    result = rake("evm:automate:export DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml")
    assert result.success, result.output
    assert appliance.ssh_client.run_command(
        "ls /root/QECliTesting.yaml").success, "Could not verify export!"


@pytest.mark.tier(3)
def test_evm_automate_simulate_upstream(rake, qe_ae_data, appliance):
    """This test checks whether CLI simulation works.

    Prerequisities:
        * ``data/cli/QECliTesting.yaml`` file imported

    Steps:
        * Run ``evm:automate:simulate DOMAIN=QECliTesting NAMESPACE=System CLASS=Request
            INSTANCE=touch`` rake task
        * Verify the file ``/var/www/miq/vmdb/check_file`` exists and it contains string
            ``check content``

    Polarion:
        assignee: sbulage
        caseimportance: low
        casecomponent: Automate
        initialEstimate: 1/4h
    """
    appliance.ssh_client.run_command("rm -f /var/www/miq/vmdb/check_file")
    result = rake(
        "evm:automate:simulate DOMAIN=QECliTesting NAMESPACE=System CLASS=Request INSTANCE=touch")
    assert result.success, result.output
    result = appliance.ssh_client.run_command("cat /var/www/miq/vmdb/check_file")
    assert result.success, "Could not find the file created by AE policy"
    assert result.output.strip() == "check content", "The file has wrong contents"


@pytest.mark.tier(1)
@pytest.mark.smoke
def test_evm_automate_convert(request, rake, appliance):
    """This test checks whether conversion from older XML format works.

    Prerequisities:
        * ``data/qe_event_handler.xml`` file.

    Steps:
        * Upload the testing file to the appliance.
        * Convert the file to ZIP using ``evm:automate:convert`` rake task
        * Import the ZIP file using ``evm:automate_import`` rake task.
        * Use ``evm:automate:extract_methods FOLDER=/some_folder`` and verify that a file named
            ``relay_events.rb`` is present in the directory hierarchy.

    Polarion:
        assignee: sbulage
        casecomponent: Automate
        initialEstimate: 1/6h
    """
    appliance.ssh_client.put_file(
        data_path.join("qe_event_handler.xml").strpath, "/root/convert_test.xml")
    request.addfinalizer(lambda: appliance.ssh_client.run_command("rm -f /root/convert_test.xml"))
    result = rake(
        "evm:automate:convert DOMAIN=Default FILE=/root/convert_test.xml "
        "ZIP_FILE=/root/convert_test.zip")
    request.addfinalizer(lambda: appliance.ssh_client.run_command("rm -f /root/convert_test.zip"))
    assert result.success, result.output
    result = appliance.ssh_client.run_command("ls -l /root/convert_test.zip")
    assert result.success, result.output
    result = rake(
        "evm:automate:import ZIP_FILE=/root/convert_test.zip DOMAIN=Default OVERWRITE=true "
        "PREVIEW=false SYSTEM=false")
    assert result.success, result.output
    # Extract the methods so we can see if it was imported
    result = rake("evm:automate:extract_methods FOLDER=/root/automate_methods")
    request.addfinalizer(lambda: appliance.ssh_client.run_command("rm -rf /root/automate_methods"))
    assert result.success, result.output
    result = appliance.ssh_client.run_command(
        "find /root/automate_methods | grep 'relay_events[.]rb$'")
    assert result.success, "Could not find the method in the extracted methods directory"
