import pytest


from fixtures.artifactor_plugin import fire_art_hook

from cfme.utils.log import logger
from cfme.utils.path import data_path
from cfme.utils.appliance import DummyAppliance



@pytest.fixture(scope="session", autouse=True)
def ensure_websocket_role_disabled(appliance):
    # TODO: This is a temporary solution until we find something better.
    if isinstance(appliance, DummyAppliance):
        return
    server_settings = appliance.server.settings
    roles = server_settings.server_roles_db
    if 'websocket' in roles and roles['websocket']:
        logger.info('Disabling the websocket role to ensure we get no intrusive popups')
        server_settings.disable_server_roles('websocket')


@pytest.fixture(scope="session", autouse=True)
def fix_merkyl_workaround(request, appliance):
    """Workaround around merkyl not opening an iptables port for communication"""
    if isinstance(appliance, DummyAppliance):
        return
    ssh_client = appliance.ssh_client
    if ssh_client.run_command('test -s /etc/init.d/merkyl').rc != 0:
        logger.info('Rudely overwriting merkyl init.d on appliance;')
        local_file = data_path.join("bundles").join("merkyl").join("merkyl")
        remote_file = "/etc/init.d/merkyl"
        ssh_client.put_file(local_file.strpath, remote_file)
        ssh_client.run_command("service merkyl restart")
        fire_art_hook(
            request.config,
            'setup_merkyl',
            ip=appliance.address)


@pytest.fixture(scope="session", autouse=True)
def fix_missing_hostname(appliance):
    """Fix for hostname missing from the /etc/hosts file

    Note: Affects RHOS-based appliances but can't hurt the others so
          it's applied on all.
    """
    if isinstance(appliance, DummyAppliance):
        return
    ssh_client = appliance.ssh_client
    logger.info("Checking appliance's /etc/hosts for its own hostname")
    if ssh_client.run_command('grep $(hostname) /etc/hosts').rc != 0:
        logger.info("Adding it's hostname to its /etc/hosts")
        # Append hostname to the first line (127.0.0.1)
        ret = ssh_client.run_command('sed -i "1 s/$/ $(hostname)/" /etc/hosts')
        if ret.rc == 0:
            logger.info("Hostname added")
        else:
            logger.error("Failed to add hostname")
