#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""
import click
import tempfile
from cached_property import cached_property
from cfme.utils import os
from cfme.utils.conf import cfme_data
from functools import partial
from .setup_ansible import setup_ansible
from scripts.repo_gen import process_url, build_file


def get_appliance(appliance_ip):
    """Checks an appliance is not None and if so, loads the appropriate things"""
    from cfme.utils.appliance import IPAppliance, get_or_create_current_appliance
    if not appliance_ip:
        app = get_or_create_current_appliance()
    else:
        app = IPAppliance(hostname=appliance_ip)
    return app


@click.group(help='Helper commands for appliances')
def main():
    """Main appliance group"""
    pass


@main.command('upgrade', help='Upgrades an appliance to latest Z-stream')
@click.argument('appliance-ip', default=None, required=False)
@click.option('--cfme-only', is_flag=True, help='Upgrade cfme packages only')
@click.option('--update-to', default='5.9.z', help='Must be 5.8.z or (5.9.z is default)')
def upgrade_appliance(appliance_ip, cfme_only, update_to):
    """Upgrades an appliance"""
    supported_version_repo_map = {'5.8.z': 'update_url_58', '5.9.z': 'update_url_59'}
    assert update_to in supported_version_repo_map, "{} is not a supported version".format(
        update_to
    )
    update_url = supported_version_repo_map[update_to]
    if appliance_ip:
        print('Connecting to {}'.format(appliance_ip))
    else:
        print('Fetching appliance from env.local.yaml')
    app = get_appliance(appliance_ip)
    print('Extending appliance partitions')
    app.db.extend_partition()
    urls = process_url(cfme_data['basic_info'][update_url])
    output = build_file(urls)
    print('Adding update repo to appliance')
    with tempfile.NamedTemporaryFile('w') as f:
        f.write(output)
        f.flush()
        os.fsync(f.fileno())
        app.ssh_client.put_file(
            f.name, '/etc/yum.repos.d/update.repo')
    ver = '95' if app.version >= '5.8' else '94'
    cfme = '-y'
    if cfme_only:
        cfme = 'cfme -y'
    print('Stopping EVM')
    app.evmserverd.stop()
    print('Running yum update')
    rc, out = app.ssh_client.run_command('yum update {}'.format(cfme), timeout=3600)
    assert rc == 0, "update failed {}".format(out)
    print('Running database migration')
    rc, out = app.ssh_client.run_rake_command("db:migrate", timeout=300)
    assert rc == 0, "Failed to migrate new database: {}".format(out)
    rc, out = app.ssh_client.run_rake_command("evm:automate:reset", timeout=300)
    assert rc == 0, "Failed to reset automate: {}".format(out)
    rc, out = app.ssh_client.run_rake_command(
        'db:migrate:status 2>/dev/null | grep "^\s*down"', timeout=30)
    assert rc != 0, "Migration failed; migrations in 'down' state found: {}".format(out)
    print('Restarting postgres service')
    rc, out = app.ssh_client.run_command('systemctl restart rh-postgresql{}-postgresql'.format(ver))
    assert rc == 0, "Failed to restart postgres: {}".format(out)
    print('Starting EVM')
    app.start_evm_service()
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


@main.command('setup-ansible', help='Setups embedded ansible on an appliance')
@click.argument('appliance_ip', default=None, required=False)
@click.option('--license', required=True, type=click.Path(exists=True))
def setup_embedded_ansible(appliance_ip, license):
    """Setups embedded ansible on an appliance"""
    app = get_appliance(appliance_ip)
    if not app.is_downstream:
        setup_ansible(app, license)
    else:
        print("It can be done only against upstream appliances.")


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
