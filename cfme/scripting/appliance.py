#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""

from cached_property import cached_property
import click

from functools import partial

from utils.appliance import IPAppliance


@click.group(help='Helper commands for appliances')
def main():
    """Main appliance group"""
    pass


@click.group(help='Helper commands for db')
def db():
    """db related command group"""
    pass


main.add_command(db)
groups = {
    'main': main,
    'db': db
}


@main.command('reboot', help='Reboots a provider')
@click.argument('appliance_ip')
@click.option('--wait_for_ui', is_flag=True, default=True)
def reboot_appliance(appliance_ip, wait_for_ui):
    """Reboots an appliance"""
    app = IPAppliance(appliance_ip)
    app.reboot(wait_for_ui)


# Useful Properties
methods_to_install = [
    'address',
    'build',
    'build_date',
    'build_datetime',
    'company_name',
    ('db', 'db_address'),
    ('db', 'db_has_database'),
    ('db', 'db_has_tables'),
    ('db', 'db_online'),
    ('db', 'db_partition_extended'),
    'default_zone',
    'evm_id',
    'get_host_address',
    'guid',
    'has_cli',
    'has_non_os_infra',
    'has_os_infra',
    'hostname',
    ('db', 'is_db_enabled'),
    ('db', 'is_db_internal'),
    ('db', 'is_db_ready'),
    'is_downstream',
    'is_embedded_ansible_running',
    'is_embedded_ensible_role_enabled',
    'is_idle',
    'is_miqqe_patch_candidate',
    'is_ssh_running',
    'is_storage_enabled',
    'is_supervisord_running',
    'managed_provider_names',
    'miqqe_patch_applied',
    'miqqe_version',
    'os_version',
    ('db', 'postgres_version'),
    'product_name',
    'swap',
    'ui_port',
    'url',
    'version',
]


def fn(method, *args, **kwargs):
    """Helper to access the right properties"""
    app = IPAppliance(kwargs['appliance_ip'])
    descriptor = getattr(IPAppliance, method)
    if isinstance(descriptor, (cached_property, property)):
        out = getattr(app, method)
    else:
        out = getattr(app, method)(*args, **kwargs)
    if out is not None:
        print(out)


for method in methods_to_install:
    if isinstance(method, tuple):
        group, method = method
    else:
        group = 'main'
    command = click.Command(
        method.replace('_', '-'),
        short_help='Returns the {} property'.format(method),
        callback=partial(fn, method), params=[click.Argument(['appliance_ip'])])
    groups[group].add_command(command)


if __name__ == "__main__":
    main()
