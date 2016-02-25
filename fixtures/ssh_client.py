import pytest

import diaper
from fixtures.pytest_store import store
from utils.log import logger
from utils import ssh


@pytest.fixture(scope="function")
def ssh_client(uses_ssh):
    """SSH Client Fixture

    Usage:

        def test_ssh(ssh_client):
            # Run a basic command
            result = ssh_client.run_command('ls -al')
            # rc is the numeric return code from the called command,
            # so 0 means everything is OK.
            assert result.rc == 0
            # and the output is available, too
            print(result.output)

            # Run a task using the CFME rails runner CLI
            ssh_client.run_rails_command('do stuff')

            # More useful: Run a rake task using the correct invokation
            ssh_client.run_rake_command('evm:stop')

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
    return store.current_appliance.ssh_client


@pytest.fixture(scope="module")
def ssh_client_modscope(uses_ssh):
    """See :py:func:`ssh_client`."""
    return store.current_appliance.ssh_client


@pytest.mark.hookwrapper
def pytest_sessionfinish(session, exitstatus):
    """Loop through the appliance stack and close ssh connections"""

    for appliance in store.appliance_stack:
        logger.debug('Closing ssh connection on {}'.format(appliance.address))
        try:
            appliance.ssh_client.close()
        except:
            logger.debug('Closing ssh connection on {} failed, but ignoring'.format(
                appliance.address))
            pass
    for session in ssh._client_session:
        with diaper:
            session.close()
    yield
