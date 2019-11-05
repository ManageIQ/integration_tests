# -*- coding: utf-8 -*-
import pytest

from cfme.utils.appliance import DummyAppliance
pytestmark = [
    pytest.mark.non_destructive,
]


@pytest.fixture(autouse=True)
def check_appliance(appliance):
    if isinstance(appliance, DummyAppliance):
        pytest.skip('Dummy appliance not supported')


def test_ssh_client_run_command(appliance):
    # Make sure the ssh command runner works
    result = appliance.ssh_client.run_command('echo Testing!')
    assert result.success
    assert 'Testing!' in result.output


def test_scp_client_can_put_a_file(appliance, tmpdir):
    # Make sure we can put a file, get a file, and they all match
    tmpfile = tmpdir.mkdir("sub").join("temp.txt")
    tmpfile.write("content")
    appliance.ssh_client.put_file(str(tmpfile), '/tmp')
    result = appliance.ssh_client.run_command("ls /tmp/{}".format(tmpfile.basename))
    assert result.success
    assert tmpfile.basename in result.output
    appliance.ssh_client.get_file("/tmp/{}".format(tmpfile.basename), str(tmpdir))
    assert "content" in tmpfile.read()
    # Clean up the server
    appliance.ssh_client.run_command("rm -f /tmp/{}".format(tmpfile.basename))
