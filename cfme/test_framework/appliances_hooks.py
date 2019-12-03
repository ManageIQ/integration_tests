from cfme.utils.log import logger


def pytest_appliance_setup(config):
    pass


def pytest_appliance_teardown(config):
    pass


def ensure_websocket_role_disabled(appliance):
    server_settings = appliance.server.settings
    roles = server_settings.server_roles_db
    if 'websocket' in roles and roles['websocket']:
        logger.info('Disabling the websocket role to ensure we get no intrusive popups')
        server_settings.disable_server_roles('websocket')


def fix_missing_hostname(appliance):
    """Fix for hostname missing from the /etc/hosts file

    Note: Affects RHOS-based appliances but can't hurt the others so
          it's applied on all.
    """
    logger.debug("Checking appliance's /etc/hosts for a resolvable hostname")
    hosts_grep_cmd = 'grep {} /etc/hosts'.format(appliance.get_resolvable_hostname())
    with appliance.ssh_client as ssh_client:
        if ssh_client.run_command(hosts_grep_cmd).failed:
            logger.info('Setting appliance hostname')
            if not appliance.set_resolvable_hostname():
                # not resolvable, just use hostname output through appliance_console_cli to modify
                cli_hostname = ssh_client.run_command('hostname').output.rstrip('\n')
                logger.warning('Unable to resolve hostname, using `hostname`: %s', cli_hostname)
                appliance.appliance_console_cli.set_hostname(cli_hostname)

            if ssh_client.run_command('grep $(hostname) /etc/hosts').failed:
                logger.error('Failed to mangle /etc/hosts')


def set_session_timeout(appliance):
    appliance.set_session_timeout(86400)
