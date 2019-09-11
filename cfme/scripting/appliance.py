#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""
from functools import partial

import click
from cached_property import cached_property

from cfme.utils.conf import env
from cfme.utils.config_data import cfme_data


def get_appliance(appliance_ip):
    """Checks an appliance is not None and if so, loads the appropriate things"""
    from cfme.utils.appliance import IPAppliance, load_appliances_from_config, stack
    if not appliance_ip:
        app = load_appliances_from_config(env)[0]
    else:
        app = IPAppliance(hostname=appliance_ip)
    stack.push(app)  # ensure safety from bad code, phase out later
    return app


@click.group(help='Helper commands for appliances')
def main():
    """Main appliance group"""
    pass


@main.command('upgrade', help='Upgrades an appliance to latest Z-stream')
@click.argument('appliance-ip', default=None, required=False)
@click.option('--cfme-only', is_flag=True, help='Upgrade cfme packages only')
@click.option('--update-to', default='5.9.z', help='Supported versions 5.9.z,'
              ' 5.10.z (.z means latest and default is 5.9.z)')  # leaving 59z support for upgrades
def upgrade_appliance(appliance_ip, cfme_only, update_to):
    """Upgrades an appliance"""
    supported_version_repo_map = {
        '5.9.z': 'update_url_59', '5.10.z': 'update_url_510',
    }
    assert update_to in supported_version_repo_map, "{} is not a supported version".format(
        update_to
    )
    update_url = supported_version_repo_map[update_to]
    if appliance_ip:
        print('Connecting to {}'.format(appliance_ip))
    else:
        print('Fetching appliance from env.local.yaml')
    app = get_appliance(appliance_ip)
    assert app.version > '5.7', "{} is not supported, must be 5.7 or higher".format(app.version)
    print('Extending appliance partitions')
    app.db.extend_partition()
    urls = cfme_data['basic_info'][update_url]
    print('Adding update repo to appliance')
    app.ssh_client.run_command(
        "curl {} -o /etc/yum.repos.d/update.repo".format(urls)
    )
    cfme = '-y'
    if cfme_only:
        cfme = 'cfme -y'
    print('Stopping EVM')
    app.evmserverd.stop()
    print('Running yum update')
    result = app.ssh_client.run_command('yum update {}'.format(cfme), timeout=3600)
    assert result.success, "update failed {}".format(result.output)
    print('Running database migration')
    app.db.migrate()
    app.db.automate_reset()
    print('Restarting postgres service')
    app.db_service.restart()
    print('Starting EVM')
    app.evmserverd.start()
    print('Waiting for webui')
    app.wait_for_web_ui()
    print('Appliance upgrade completed')


@main.command('migrate', help='Restores/migrates database from file or downloaded')
@click.argument('appliance-ip', default=None, required=True)
@click.option('--db-url', default=None, help='Download a backup file')
@click.option('--keys-url', default=None, help='URL for matching db v2key and GUID if available')
@click.option('--backup', default=None, help='Location of local backup file, including file name')
def backup_migrate(appliance_ip, db_url, keys_url, backup):
    """Restores and migrates database backup on an appliance"""
    print('Connecting to {}'.format(appliance_ip))
    app = get_appliance(appliance_ip)
    if db_url:
        print('Downloading database backup')
        result = app.ssh_client.run_command(
            'curl -o "/evm_db.backup" "{}"'.format(db_url), timeout=30)
        assert result.success, "Failed to download database: {}".format(result.output)
        backup = '/evm_db.backup'
    else:
        backup = backup
    print('Stopping EVM')
    app.evmserverd.stop()
    print('Dropping/Creating database')
    app.db.drop()
    app.db.create()
    print('Restoring database from backup')
    result = app.ssh_client.run_command(
        'pg_restore -v --dbname=vmdb_production {}'.format(backup), timeout=600)
    assert result.success, "Failed to restore new database: {}".format(result.output)
    print('Running database migration')
    app.db.migrate()
    app.db.automate_reset()
    if keys_url:
        result = app.ssh_client.run_command(
            'curl -o "/var/www/miq/vmdb/certs/v2_key" "{}v2_key"'.format(keys_url), timeout=15)
        assert result.success, "Failed to download v2_key: {}".format(result.output)
        result = app.ssh_client.run_command(
            'curl -o "/var/www/miq/vmdb/GUID" "{}GUID"'.format(keys_url), timeout=15)
        assert result.success, "Failed to download GUID: {}".format(result.output)
    else:
        app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    print('Restarting postgres service')
    app.db_service.restart()
    print('Starting EVM')
    app.evmserverd.start()
    print('Waiting for webui')
    app.wait_for_web_ui()
    print('Appliance upgrade completed')


@main.command('reboot', help='Reboots the appliance')
@click.argument('appliance_ip', default=None, required=False)
@click.option('--wait-for-ui', is_flag=True, default=True)
def reboot_appliance(appliance_ip, wait_for_ui):
    """Reboots an appliance"""
    app = get_appliance(appliance_ip)
    app.reboot(wait_for_ui)


@main.command('setup-webmks', help='Setups VMware WebMKS on an appliance by downloading'
            'and extracting SDK to required location')
@click.argument('appliance_ip', default=None, required=False)
def config_webmks(appliance_ip):
    appliance = get_appliance(appliance_ip)
    server_settings = appliance.server.settings
    server_settings.update_vmware_console({'console_type': 'VMware WebMKS'})
    roles = server_settings.server_roles_db
    if 'websocket' in roles and not roles['websocket']:
        server_settings.enable_server_roles('websocket')


# Useful Properties
methods_to_install = [
    'is_db_enabled',
    'managed_provider_names',
    'miqqe_version',
    'os_version',
    'swap',
    'miqqe_patch_applied']


def fn(method, *args, **kwargs):
    """Helper to access the right properties"""
    from cfme.utils.appliance import IPAppliance
    appliance_ip = kwargs.get('appliance_ip', None)
    app = get_appliance(appliance_ip)
    descriptor = getattr(IPAppliance, method)
    if isinstance(descriptor, (cached_property, property)):
        out = getattr(app, method)
    else:
        out = getattr(app, method)(*args, **kwargs)
    if out is not None:
        print(out)


for method in methods_to_install:
    command = click.Command(
        method.replace('_', '-'),
        short_help='Returns the {} property'.format(method),
        callback=partial(fn, method), params=[
            click.Argument(['appliance_ip'], default=None, required=False)])
    main.add_command(command)

if __name__ == "__main__":
    main()
