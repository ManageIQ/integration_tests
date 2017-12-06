import click
import re
import sys

from cfme.test_framework.sprout.client import SproutClient
from collections import namedtuple
from cfme.utils.conf import credentials, cfme_data
from cfme.utils.appliance import IPAppliance
from wait_for import wait_for

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])
pwd = credentials['database']['password']


def tot_time(string):
    """Takes the lease string and converts it to minutes to pass to sprout"""
    mtch = re.match('^((?P<days>\d+)+d)?\s?((?P<hours>\d+)+h)?\s?((?P<minutes>\d+)+m)?\s?', string)
    tot = int(mtch.group('days') or 0) * 24 * 60
    tot += int(mtch.group('hours') or 0) * 60
    tot += int(mtch.group('minutes')or 0)
    return tot


def provision_appliances(count, cfme_version, provider, lease_time):
    sprout_client = SproutClient.from_config()
    apps, request_id = sprout_client.provision_appliances(version=str(cfme_version),
        count=count, preconfigured=False, lease_time=lease_time, provider=provider)
    return apps, request_id


@click.group(help='Commands to set up appliance environments with version arg and lease option')
def main():
    """Main setup-env group"""
    pass


@main.command('distributed', help='Sets up distributed environment')
@click.option('--cfme-version', required=True)
@click.option('--provider', default=None, help='Specify sprout provider')
@click.option('--lease', default='3h', help='Set pool lease time, example: 1d4h30m')
@click.option('--desc', default='Distributed appliances', help='Set description of the pool')
def setup_distributed_env(cfme_version, provider, lease, desc):
    lease_time = tot_time(lease)
    """multi appliance single region configuration (distributed setup, 1st appliance has
    a local database and workers, 2nd appliance has workers pointing at 1st appliance)"""
    print("Provisioning and configuring distributed environment")
    apps, request_id = provision_appliances(count=2, cfme_version=cfme_version, provider=provider,
        lease_time=lease_time)
    sprout_client = SproutClient.from_config()
    sprout_client.set_pool_description(request_id, desc)
    opt = '5' if cfme_version >= "5.8" else '8'
    ip0 = apps[0].hostname
    ip1 = apps[1].hostname
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
    print("Appliance pool lease time is {}".format(lease))


@main.command('ha', help='Sets up high availability environment')
@click.option('--cfme-version', required=True)
@click.option('--provider', default=cfme_data.get('basic_info', {}).get('ha_provider'),
    help='Specify sprout provider, must not be RHOS')
@click.option('--lease', default='3h', help='set pool lease time, example: 1d4h30m')
@click.option('--desc', default='HA configuration', help='Set description of the pool')
def setup_ha_env(cfme_version, provider, lease, desc):
    lease_time = tot_time(lease)
    """multi appliance setup consisting of dedicated primary and standy databases with a single
    UI appliance."""
    print("Provisioning and configuring HA environment")
    apps, request_id = provision_appliances(count=3, cfme_version=cfme_version, provider=provider,
        lease_time=lease_time)
    sprout_client = SproutClient.from_config()
    sprout_client.set_pool_description(request_id, desc)
    ip0 = apps[0].hostname
    ip1 = apps[1].hostname
    ip2 = apps[2].hostname
    opt = '5' if cfme_version >= "5.8" else '8'
    rep = '6' if cfme_version >= "5.8" else '9'
    mon = '9' if cfme_version >= "5.8" else '12'
    port = (ip0, '') if cfme_version >= "5.8" else (ip0,)
    command_set0 = ('ap', '', opt, '1', '1', '1', 'y', pwd, TimedCommand(pwd, 360), '')
    apps[0].appliance_console.run_commands(command_set0)
    wait_for(lambda: apps[0].db.is_dedicated_active)
    print("Dedicated database provisioned and configured {}".format(ip0))
    command_set1 = ('ap', '', opt, '1', '2', '1', 'y') + port + ('', '', pwd,
        TimedCommand(pwd, 360), '')
    apps[1].appliance_console.run_commands(command_set1)
    apps[1].wait_for_evm_service()
    apps[1].wait_for_web_ui()
    print("Non-VMDB appliance provisioned and region created {}".format(ip1))
    command_set2 = ('ap', '', rep, '1', '1', '', '', pwd, pwd, ip0, 'y', '')
    apps[0].appliance_console.run_commands(command_set2)
    print("Primary HA node configured {}".format(ip0))
    command_set3 = ('ap', '', rep, '2', '1', '2', '', '', pwd, pwd, ip0, ip2, 'y',
        TimedCommand('y', 300), '')
    apps[2].appliance_console.run_commands(command_set3)
    print("Secondary HA node provision and configured {}".format(ip2))
    command_set4 = ('ap', '', mon, '1', '')
    apps[1].appliance_console.run_commands(command_set4)
    print("HA configuration complete")
    print("Appliance pool lease time is {}".format(lease))


@main.command('replicated', help='Sets up replicated environment')
@click.option('--cfme-version', required=True)
@click.option('--provider', default=None, help='Specify sprout provider')
@click.option('--lease', default='3h', help='set pool lease time, example: 1d4h30m')
@click.option('--sprout-poolid', default=None, help='Specify ID of existing pool')
@click.option('--desc', default='Replicated appliances', help='Set description of the pool')
def setup_replication_env(cfme_version, provider, lease, sprout_poolid, desc):
    lease_time = tot_time(lease)
    """Multi appliance setup with multi region and replication from remote to global"""
    required_app_count = 2
    if sprout_poolid:
        sprout_client = SproutClient.from_config()
        if sprout_client.call_method('pool_exists', sprout_poolid):
            sprout_pool = sprout_client.call_method('request_check', sprout_poolid)
            if len(sprout_pool['appliances']) >= required_app_count:
                print("Processing pool...")
                apps = []
                for app in sprout_pool['appliances']:
                    apps.append(IPAppliance(app['ip_address']))
            else:
                sys.exit("Pool does not meet the minimum size requirements!")
        else:
            sys.exit("Pool not found!")

    else:
        print("Provisioning appliances")
        apps, request_id = provision_appliances(
            count=required_app_count, cfme_version=cfme_version,
            provider=provider, lease_time=lease_time
        )
        print("Appliance pool lease time is {}".format(lease))
    sprout_client = SproutClient.from_config()
    sprout_client.set_pool_description(request_id, desc)
    print("Configuring replicated environment")
    ip0 = apps[0].hostname
    ip1 = apps[1].hostname
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
    apps[0].add_pglogical_replication_subscription(apps[1].hostname)
    print("Done!")


if __name__ == "__main__":
    main()
