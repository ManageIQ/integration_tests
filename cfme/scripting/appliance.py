#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""

import click
from cached_property import cached_property
from functools import partial
from collections import namedtuple
from utils.appliance import get_or_create_current_appliance
from utils.conf import credentials, cfme_data
from cfme.test_framework.sprout.client import SproutClient
from wait_for import wait_for
from .setup_ansible import setup_ansible


def get_appliance(appliance_ip):
    """Checks an appliance is not None and if so, loads the appropriate things"""
    from cfme.utils.appliance import IPAppliance, get_or_create_current_appliance
    if not appliance_ip:
        app = get_or_create_current_appliance()
    else:
        app = IPAppliance(appliance_ip)
    return app


def provision_appliances(count, cfme_version, provider):
    sprout_client = SproutClient.from_config()
    apps, request_id = sprout_client.provision_appliances(version=str(cfme_version),
        count=count, preconfigured=False, lease_time=360, provider=provider)
    return apps


@click.group(help='Helper commands for appliances')
def main():
    """Main appliance group"""
    pass


@main.command('reboot', help='Reboots the appliance')
@click.argument('appliance_ip', default=None, required=False)
@click.option('--wait-for-ui', is_flag=True, default=True)
def reboot_appliance(appliance_ip, wait_for_ui):
    """Reboots an appliance"""
    app = get_appliance(appliance_ip)
    app.reboot(wait_for_ui)


@main.command('setup_ansible', help='Setups embedded ansible on an appliance')
@click.argument('appliance_ip', default=None, required=False)
@click.option('--license', required=True, type=click.Path(exists=True))
def setup_embedded_ansible(appliance_ip, license):
    """Setups embedded ansible on an appliance"""
    app = get_appliance(appliance_ip)
    if not app.is_downstream:
        setup_ansible(app, license)
    else:
        print("It can be done only against upstream appliances.")


@main.command('setup_environment', help='Provisions and configures appliance environments')
@click.option('--cfme_version', default=None)
@click.option('--ha', 'mode', flag_value='ha')
@click.option('--distributed', 'mode', flag_value='distributed')
@click.option('--replication', 'mode', flag_value='replication')
def setup_appliances(cfme_version, mode):
    """setup up appliances in a desired configuration"""
    TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])

    pwd = credentials['database']['password']
    cfme_version = cfme_version or get_or_create_current_appliance().version
    provider = cfme_data['basic_info']['ha_provider']

    if mode == 'distributed':
        """multi appliance single region configuration (distributed setup, 1st appliance has
        a local database and workers, 2nd appliance has workers pointing at 1st appliance)"""

        print "Provisioning and configuring distributed environment"

        apps = provision_appliances(count=2, cfme_version=cfme_version)
        opt = '5' if cfme_version >= "5.8" else '8'
        ip0 = apps[0].address
        port = (ip0, '') if cfme_version >= "5.8" else (ip0,)

        command_set0 = ('ap', '', opt, '1', '1', 'y', '1', 'n', '1', pwd,
            TimedCommand(pwd, 360), '')

        apps[0].appliance_console.run_commands(command_set0)
        apps[0].wait_for_evm_service()
        apps[0].wait_for_web_ui()

        print "VMDB appliance provision and configured"

        command_set1 = ('ap', '', opt, '2', ip0, '', pwd, '', '3') + port + ('', '',
            pwd, TimedCommand(pwd, 360), '')

        apps[1].appliance_console.run_commands(command_set1)
        apps[1].wait_for_evm_service()
        apps[1].wait_for_web_ui()

        print "Non-VMDB appliance provisioned and configured"

    elif mode == 'ha':
        """multi appliance setup consisting of dedicated primary and standy databases with a single
        UI appliance."""

        print "Provisioning and configuring HA environment"

        apps = provision_appliances(count=3, cfme_version=cfme_version,
            provider=provider)
        ip0 = apps[0].address
        ip2 = apps[2].address
        opt = '5' if cfme_version >= "5.8" else '8'
        port = (ip0, '') if cfme_version >= "5.8" else (ip0,)

        command_set0 = ('ap', '', opt, '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')

        apps[0].appliance_console.run_commands(command_set0)
        wait_for(lambda: apps[0].db.is_dedicated_active)

        print "Dedicated database provisioned and configured"

        command_set1 = ('ap', '', opt, '1', '2', '1', 'y') + port + ('', '', pwd,
                            TimedCommand(pwd, 360), '')

        apps[1].appliance_console.run_commands(command_set1)
        apps[1].wait_for_evm_service()
        apps[1].wait_for_web_ui()

        print "Non-VMDB appliance provisioned and region created"

        command_set2 = ('ap', '', '6', '1', '1', '', '', pwd, pwd, ip0, 'y', '')

        apps[0].appliance_console.run_commands(command_set2)

        print "Primary HA node configured"

        command_set3 = ('ap', '', '6', '2', '1', '2', '', '', pwd, pwd, ip0, ip2, 'y', 'y', '')

        apps[2].appliance_console.run_commands(command_set3)

        print "Secondary HA node configured"

        command_set4 = ('ap', '', '9', '1', '')

        apps[1].appliance_console.run_commands(command_set4)

        print "HA configuration complete"

    elif mode == 'replication':

        """Multi appliance setup with multi region and replication from remote to global"""

        print "Provisioning and configuring replication environment"

        apps = provision_appliances(count=2, cfme_version=cfme_version)
        ip0 = apps[0].address
        opt = '5' if cfme_version >= "5.8" else '8'

        command_set0 = ('ap', '', opt, '1', '1', 'y', '1', 'n', '99', pwd,
            TimedCommand(pwd, 360), '')

        apps[0].appliance_console.run_commands(command_set0)
        apps[0].wait_for_evm_service()
        apps[0].wait_for_web_ui()

        print "Global region appliance provisioned and configured"

        command_set1 = ('ap', '', opt, '2', ip0, '', pwd, '', '1', 'y', '1', 'n', '1', pwd,
            TimedCommand(pwd, 360), '')

        apps[1].appliance_console.run_commands(command_set1)
        apps[1].wait_for_evm_service()
        apps[1].wait_for_web_ui()

        print "Remote region appliance provisioned and configured"

        # Config remote
        print("Setup - Replication on remote appliance")
        apps[1].set_pglogical_replication(replication_type=':remote')

        # Add subscription to global
        print("Setup - Replication on global appliance")
        apps[0].set_pglogical_replication(replication_type=':global')
        apps[0].add_pglogical_replication_subscription(apps[1].address)
        print("Done!")

    else:
        raise Exception('You must select a mode, ha/distrubuted/replication')


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
