#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""
import sys
import click
from cfme.test_framework.sprout.client import SproutClient
from collections import namedtuple
from utils.conf import credentials, cfme_data
from wait_for import wait_for


def provision_appliances(count, cfme_version, provider):
    sprout_client = SproutClient.from_config()
    apps, request_id = sprout_client.provision_appliances(version=str(cfme_version),
        count=count, preconfigured=False, lease_time=180, provider=provider)
    return apps


@click.group(help='Helper commands for appliances')
def main():
    """Main appliance group"""
    pass


@main.command('setup-env', help='Provisions and configures appliances')
@click.option('--cfme-version', required=True)
@click.option('--lease-time', default=180)
@click.option('--ha', 'mode', flag_value='ha')
@click.option('--distributed', 'mode', flag_value='distributed')
@click.option('--replication', 'mode', flag_value='replication')
def setup_appliances(cfme_version, lease_time, mode):
    """setup up appliances in a desired configuration"""
    TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])
    pwd = credentials['database']['password']
    provider = None
    if mode == 'distributed':
        """multi appliance single region configuration (distributed setup, 1st appliance has
        a local database and workers, 2nd appliance has workers pointing at 1st appliance)"""
        print("Provisioning and configuring distributed environment")
        apps = provision_appliances(count=2, cfme_version=cfme_version, provider=provider,
            lease_time=lease_time)
        opt = '5' if cfme_version >= "5.8" else '8'
        ip0 = apps[0].address
        ip1 = apps[1].address
        port = (ip0, '') if cfme_version >= "5.8" else (ip0,)
        command_set0 = ('ap', '', opt, '1', '1', 'y', '1', 'n', '1', pwd,
            TimedCommand(pwd, 360), '')
        apps[0].appliance_console.run_commands(command_set0)
        apps[0].wait_for_evm_service()
        apps[0].wait_for_web_ui()
        print("VMDB appliance provisioned and configured {}".format(ip0))
        command_set1 = ('ap', '', opt, '2', ip0, '', pwd, '', '3') + port + ('', '',
            pwd, TimedCommand(pwd, 360), '')
        apps[1].appliance_console.run_commands(command_set1)
        apps[1].wait_for_evm_service()
        apps[1].wait_for_web_ui()
        print("Non-VMDB appliance provisioned and configured {}".format(ip1))
    elif mode == 'ha':
        """multi appliance setup consisting of dedicated primary and standy databases with a single
        UI appliance."""
        print("Provisioning and configuring HA environment")
        provider = cfme_data['basic_info']['ha_provider']
        apps = provision_appliances(count=3, cfme_version=cfme_version, provider=provider,
            lease_time=lease_time)
        ip0 = apps[0].address
        ip1 = apps[1].address
        ip2 = apps[2].address
        opt = '5' if cfme_version >= "5.8" else '8'
        port = (ip0, '') if cfme_version >= "5.8" else (ip0,)
        command_set0 = ('ap', '', opt, '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')
        apps[0].appliance_console.run_commands(command_set0)
        wait_for(lambda: apps[0].db.is_dedicated_active)
        print("Dedicated database provisioned and configured {}".format(ip0))
        command_set1 = ('ap', '', opt, '1', '2', '1', 'y') + port + ('', '', pwd,
            TimedCommand(pwd, 360), '')
        apps[1].appliance_console.run_commands(command_set1)
        apps[1].wait_for_evm_service()
        apps[1].wait_for_web_ui()
        print("Non-VMDB appliance provisioned and region created {}".format(ip1))
        command_set2 = ('ap', '', '6', '1', '1', '', '', pwd, pwd, ip0, 'y', '')
        apps[0].appliance_console.run_commands(command_set2)
        print("Primary HA node configured {}".format(ip0))
        command_set3 = ('ap', '', '6', '2', '1', '2', '', '', pwd, pwd, ip0, ip2, 'y', 'y', '')
        apps[2].appliance_console.run_commands(command_set3)
        print("Secondary HA node provision and configured {}".format(ip2))
        command_set4 = ('ap', '', '9', '1', '')
        apps[1].appliance_console.run_commands(command_set4)
        print("HA configuration complete")
    elif mode == 'replication':
        """Multi appliance setup with multi region and replication from remote to global"""
        print("Provisioning and configuring replication environment")
        apps = provision_appliances(count=2, cfme_version=cfme_version, provider=provider,
            lease_time=lease_time)
        ip0 = apps[0].address
        ip1 = apps[1].address
        opt = '5' if cfme_version >= "5.8" else '8'
        command_set0 = ('ap', '', opt, '1', '1', 'y', '1', 'n', '99', pwd,
            TimedCommand(pwd, 360), '')
        apps[0].appliance_console.run_commands(command_set0)
        apps[0].wait_for_evm_service()
        apps[0].wait_for_web_ui()
        print("Global region appliance provisioned and configured {}".format(ip0))
        command_set1 = ('ap', '', opt, '2', ip0, '', pwd, '', '1', 'y', '1', 'n', '1', pwd,
            TimedCommand(pwd, 360), '')
        apps[1].appliance_console.run_commands(command_set1)
        apps[1].wait_for_evm_service()
        apps[1].wait_for_web_ui()
        print("Remote region appliance provisioned and configured {}".format(ip1))
        print("Setup - Replication on remote appliance")
        apps[1].set_pglogical_replication(replication_type=':remote')
        print("Setup - Replication on global appliance")
        apps[0].set_pglogical_replication(replication_type=':global')
        apps[0].add_pglogical_replication_subscription(apps[1].address)
        print("Done!")
    else:
        print("You must select a mode, such as --ha / --distrubuted / --replication")
        sys.exit(127)


if __name__ == "__main__":
    main()
