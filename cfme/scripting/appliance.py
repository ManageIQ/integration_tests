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


def get_appliance(appliance_ip):
    """Checks an appliance is not None and if so, loads the appropriate things"""
    from utils.appliance import IPAppliance, get_or_create_current_appliance
    if not appliance_ip:
        app = get_or_create_current_appliance()
    else:
        app = IPAppliance(appliance_ip)
    return app


@click.group(help='Helper commands for appliances')
def main():
    """Main appliance group"""
    pass


@main.command('reboot', help='Reboots a provider')
@click.argument('appliance_ip', default=None, required=False)
@click.option('--wait-for-ui', is_flag=True, default=True)
def reboot_appliance(appliance_ip, wait_for_ui):
    """Reboots an appliance"""
    app = get_appliance(appliance_ip)
    app.reboot(wait_for_ui)


# Useful Properties
methods_to_install = [
    'is_db_enabled',
    'managed_provider_names',
    'miqqe_version',
    'has_os_infra',
    'os_version',
    'swap',
    'miqqe_patch_applied']


def fn(method, *args, **kwargs):
    """Helper to access the right properties"""
    from utils.appliance import IPAppliance
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
