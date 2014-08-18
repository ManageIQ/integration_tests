# -*- coding: utf-8 -*-
import pytest

from cfme.automate.explorer import Domain
from utils.log import logger
from utils.path import data_path
from utils.update import update
from utils.version import current_version

cli_path = data_path.join("cli")

pytestmark = [pytest.mark.skipif(current_version() < "5.3", reason="<5.3 does not support domains")]


@pytest.yield_fixture(scope="module")
def back_up_default_domain(ssh_client):
    ssh_client.run_command("rm -f /tmp/Default_backup.yaml")
    rc = ssh_client.run_rake_command(
        "evm:automate:export DOMAIN=Default YAML_FILE=/tmp/Default_backup.yaml "
        "PREVIEW=false OVERWRITE=true")[0]
    yield
    if rc == 0:
        rc, stdout = ssh_client.run_rake_command(
            "evm:automate:import DOMAIN=Default YAML_FILE=/tmp/Default_backup.yaml PREVIEW=false")
        if rc != 0:
            logger.exception("Could not re-improt back the Default domain!: `{}`".format(stdout))


@pytest.yield_fixture(scope="function")
def rake(ssh_client, back_up_default_domain):
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
        "evm:automate:import DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml PREVIEW=false")
    assert rc == 0, stdout
    # Now we have to enable the domain to make it work.
    qe_cli_testing = Domain(name="QECliTesting")
    if not qe_cli_testing.is_enabled:
        with update(qe_cli_testing):
            qe_cli_testing.enabled = True


@pytest.mark.smoke
def test_evm_automate_import_export_works_upstream(ssh_client, rake, soft_assert):
    ssh_client.put_file(cli_path.join("QECliTesting.yaml").strpath, "/root/QECliTesting.yaml")
    rc, stdout = rake(
        "evm:automate:import DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml PREVIEW=false")
    assert rc == 0, stdout
    ssh_client.run_command("rm -f QECliTesting.yaml")
    rc, stdout = rake("evm:automate:export DOMAIN=QECliTesting YAML_FILE=/root/QECliTesting.yaml")
    assert rc == 0, stdout
    assert ssh_client.run_command("ls /root/QECliTesting.yaml")[0] == 0, "Could not verify export!"


def test_evm_automate_simulate_upstream(rake, qe_ae_data, ssh_client):
    ssh_client.run_command("rm -f /var/www/miq/vmdb/check_file")
    rc, stdout = rake(
        "evm:automate:simulate DOMAIN=QECliTesting NAMESPACE=System CLASS=Request INSTANCE=touch")
    assert rc == 0, stdout
    rc, stdout = ssh_client.run_command("cat /var/www/miq/vmdb/check_file")
    assert rc == 0, "Could not find the file created by AE policy"
    assert stdout.strip() == "check content", "The file has wrong contents"


@pytest.mark.smoke
def test_evm_automate_convert(request, rake, ssh_client):
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
        "PREVIEW=false")
    assert rc == 0, stdout
    # Extract the methods so we can see if it was imported
    rc, stdout = rake("evm:automate:extract_methods FOLDER=/root/automate_methods")
    request.addfinalizer(lambda: ssh_client.run_command("rm -rf /root/automate_methods"))
    assert rc == 0, stdout
    rc, stdout = ssh_client.run_command("find /root/automate_methods | grep 'relay_events[.]rb$'")
    assert rc == 0, "Could not find the method in the extracted methods directory"
