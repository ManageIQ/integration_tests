# -*- coding: utf-8 -*-
import fauxfactory
import pytest

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium,
]


def test_ssh_client_run_command(ssh_client):
    # Make sure the ssh command runner works
    exit_status, output = ssh_client.run_command('echo Testing!')
    assert exit_status == 0
    assert 'Testing!' in output


def test_ssh_client_copies(ssh_client):
    ssh_client_kwargs = {
        'username': fauxfactory.gen_alphanumeric(8),
        'password': fauxfactory.gen_alphanumeric(8),
        'hostname': fauxfactory.gen_alphanumeric(8),
    }

    # Make sure the ssh copy mechanism works
    ssh_client_copy = ssh_client(**ssh_client_kwargs)
    orig_kwargs = ssh_client._connect_kwargs
    copy_kwargs = ssh_client_copy._connect_kwargs
    assert orig_kwargs['username'] != copy_kwargs['username']
    assert orig_kwargs['password'] != copy_kwargs['password']
    assert orig_kwargs['hostname'] != copy_kwargs['hostname']

    # And also make sure the ssh copy only updates new kwargs
    ssh_client_copy = ssh_client(hostname=fauxfactory.gen_alphanumeric(8))
    copy_kwargs = ssh_client_copy._connect_kwargs
    assert orig_kwargs['username'] == copy_kwargs['username']
    assert orig_kwargs['password'] == copy_kwargs['password']
    assert orig_kwargs['hostname'] != copy_kwargs['hostname']


def test_ssh_client_memoization(ssh_client):
    ssh_client_kwargs = {
        'username': fauxfactory.gen_alphanumeric(8),
        'password': fauxfactory.gen_alphanumeric(8),
        'hostname': fauxfactory.gen_alphanumeric(8),
    }
    client = ssh_client(**ssh_client_kwargs)
    client_same = ssh_client(**ssh_client_kwargs)
    assert client is client_same
    different_ssh_client_kwargs = {
        'username': fauxfactory.gen_alphanumeric(8),
        'password': fauxfactory.gen_alphanumeric(8),
        'hostname': fauxfactory.gen_alphanumeric(8),
    }
    client_different = ssh_client(**different_ssh_client_kwargs)
    assert client is not client_different


def test_scp_client_can_put_a_file(ssh_client, tmpdir):
    # Make sure we can put a file, get a file, and they all match
    tmpfile = tmpdir.mkdir("sub").join("temp.txt")
    tmpfile.write("content")
    ssh_client.put_file(str(tmpfile), '/tmp')
    exit_status, output = ssh_client.run_command("ls /tmp/%s" % tmpfile.basename)
    assert exit_status == 0
    assert tmpfile.basename in output
    ssh_client.get_file("/tmp/%s" % tmpfile.basename, str(tmpdir))
    assert "content" in tmpfile.read()
    # Clean up the server
    ssh_client.run_command("rm -f /tmp/%s" % tmpfile.basename)
