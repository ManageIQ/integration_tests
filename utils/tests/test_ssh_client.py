import pytest
from unittestzero import Assert

from utils.randomness import generate_random_string

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium,
]

def test_ssh_client_run_command(ssh_client):
    # Make sure the ssh command runner works
    exit_status, output = ssh_client.run_command('echo Testing!')
    Assert.equal(exit_status, 0)
    Assert.contains(output, 'Testing!')

def test_ssh_client_copies(ssh_client):
    ssh_client_kwargs = {
        'username': generate_random_string(),
        'password': generate_random_string(),
        'hostname': generate_random_string(),
    }

    # Make sure the ssh copy mechanism works
    ssh_client_copy = ssh_client(**ssh_client_kwargs)
    orig_kwargs = ssh_client._connect_kwargs
    copy_kwargs = ssh_client_copy._connect_kwargs
    Assert.not_equal(orig_kwargs['username'], copy_kwargs['username'])
    Assert.not_equal(orig_kwargs['password'], copy_kwargs['password'])
    Assert.not_equal(orig_kwargs['hostname'], copy_kwargs['hostname'])

    # And also make sure the ssh copy only updates new kwargs
    ssh_client_copy = ssh_client(hostname=generate_random_string())
    copy_kwargs = ssh_client_copy._connect_kwargs
    Assert.equal(orig_kwargs['username'], copy_kwargs['username'])
    Assert.equal(orig_kwargs['password'], copy_kwargs['password'])
    Assert.not_equal(orig_kwargs['hostname'], copy_kwargs['hostname'])

