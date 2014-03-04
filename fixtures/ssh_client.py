import pytest

from utils.ssh import SSHClient


@pytest.fixture
def ssh_client(uses_ssh):
    """SSH Client Fixture

    By default, it will connect to the host named in the mozwebqa baseurl on use,
    using the 'ssh' credentials in your credentials file. The mozwebqa fixture is used
    for this, which will open up a selenium browser by default. If this is undesired,
    remember to use the skip_selenium mark.

    Usage:

        @pytest.mark.skip_selenium
        def test_ssh(ssh_client):
            # Run a basic command
            exit_status, output = ssh_client.run_command('ls -al')
            # Exit status is the numeric return code from the called command,
            # so 0 means everything is OK.
            assert exit_status == 0

            # Run a task using the CFME rails runner CLI
            exit_status, output = ssh_client.run_rails_command('do stuff')

            # More useful: Run a rake task using the correct invokation
            exit_status, output = ssh_client.run_rake_command('evm:stop')

    Additionally, the ssh_client fixture can be used to create other ssh clients,
    if you need to connect to multiple hosts in a test run::

        def test_multiple_ssh(ssh_client):
            # Normal behavior still works
            ssh_client.run_command('some_command')

            # Instantiate a client aimed at a different hostname
            ssh_client_2 = ssh_client(hostname='different.host')
            ssh_client_2.run_command('some_other_command')

            # Username and password can be changed, too
            ssh_client_3 = ssh_client(username='foo', password='bar')

            # Hint: **credentials['credentials_key'], e.g.
            ssh_client_4 = ssh_client(hostname='different.host', **credentials['ssh'])


    """
    return SSHClient()
