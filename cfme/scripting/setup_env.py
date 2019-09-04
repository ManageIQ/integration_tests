import random
import re
import sys
from collections import namedtuple
from itertools import cycle

import click
from wait_for import wait_for

from cfme.test_framework.sprout.client import SproutClient
from cfme.utils.appliance import IPAppliance
from cfme.utils.appliance import stack
from cfme.utils.conf import credentials
from cfme.utils.providers import get_crud
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])
pwd = None


def tot_time(string):
    """Takes the lease string and converts it to minutes to pass to sprout"""
    mtch = re.match(r'^((?P<days>\d+)+d)?\s?((?P<hours>\d+)+h)?\s?((?P<minutes>\d+)+m)?\s?',
                    string)
    tot = int(mtch.group('days') or 0) * 24 * 60
    tot += int(mtch.group('hours') or 0) * 60
    tot += int(mtch.group('minutes')or 0)
    return tot


def provision_appliances(count, cfme_version, provider_type, provider, lease_time):
    sprout_client = SproutClient.from_config()
    apps, request_id = sprout_client.provision_appliances(version=str(cfme_version),
        count=count, preconfigured=False, lease_time=lease_time, provider_type=provider_type,
        provider=provider)
    return apps, request_id


@click.group(help='Commands to set up appliance environments with version arg and lease option')
def main():
    """Main setup-env group"""
    global pwd  # hack
    pwd = credentials['database']['password']


@main.command('distributed', help='Sets up distributed environment')
@click.option('--cfme-version', required=True)
@click.option('--provider-type', default='rhevm', help='Specify sprout provider_type')
@click.option('--provider', default=None, help='Specify sprout provider, overrides provider_type')
@click.option('--lease', default='3h', help='Set pool lease time, example: 1d4h30m')
@click.option('--desc', default='Distributed appliances', help='Set description of the pool')
def setup_distributed_env(cfme_version, provider_type, provider, lease, desc):
    lease_time = tot_time(lease)
    provider_type = None if provider else provider_type
    """multi appliance single region configuration (distributed setup, 1st appliance has
    a local database and workers, 2nd appliance has workers pointing at 1st appliance)"""
    print("Provisioning and configuring distributed environment")
    apps, request_id = provision_appliances(count=2, cfme_version=cfme_version,
        provider_type=provider_type, provider=provider, lease_time=lease_time)
    sprout_client = SproutClient.from_config()
    sprout_client.set_pool_description(request_id, desc)
    opt = '5' if cfme_version >= "5.8" else '8'
    ip0 = apps[0].hostname
    ip1 = apps[1].hostname
    port = (ip0, '') if cfme_version >= "5.8" else (ip0,)
    command_set0 = ('ap', '', opt, '1', '1', 'y', '1', 'n', '1', pwd,
        TimedCommand(pwd, 360), '')
    apps[0].appliance_console.run_commands(command_set0)
    apps[0].evmserverd.wait_for_running()
    apps[0].wait_for_web_ui()
    print("VMDB appliance provisioned and configured {}".format(ip0))
    command_set1 = ('ap', '', opt, '2', ip0, '', pwd, '', '3') + port + ('', '',
        pwd, TimedCommand(pwd, 360), '')
    apps[1].appliance_console.run_commands(command_set1)
    apps[1].evmserverd.wait_for_running()
    apps[1].wait_for_web_ui()
    print("Non-VMDB appliance provisioned and configured {}".format(ip1))
    print("Appliance pool lease time is {}".format(lease))


@main.command('ha', help='Sets up high availability environment')
@click.option('--cfme-version', required=True)
@click.option('--provider-type', default='rhevm', help='Specify provider type, must not be RHOS')
@click.option('--provider', default=None, help='Specify sprout provider, overrides provider_type')
@click.option('--lease', default='3h', help='set pool lease time, example: 1d4h30m')
@click.option('--desc', default='HA configuration', help='Set description of the pool')
def setup_ha_env(cfme_version, provider_type, provider, lease, desc):
    lease_time = tot_time(lease)
    provider_type = None if provider else provider_type
    """multi appliance setup consisting of dedicated primary and standy databases with a single
    UI appliance."""
    print("Provisioning and configuring HA environment")
    apps, request_id = provision_appliances(count=3, cfme_version=cfme_version,
        provider_type=provider_type, provider=provider, lease_time=lease_time)
    sprout_client = SproutClient.from_config()
    sprout_client.set_pool_description(request_id, desc)
    ip0 = apps[0].hostname
    ip1 = apps[1].hostname
    ip2 = apps[2].hostname
    opt = '5' if cfme_version >= "5.8" else '8'
    rep = '6' if cfme_version >= "5.8" else '9'
    mon = VersionPicker({
        Version.lowest(): '12',
        '5.8': '9',
        '5.9.3': '8'
    }).pick(cfme_version)
    port = (ip0, '') if cfme_version >= "5.8" else (ip0,)
    command_set0 = ('ap', '', opt, '1', '1', '1', 'y', pwd, TimedCommand(pwd, 360), '')
    apps[0].appliance_console.run_commands(command_set0)
    wait_for(lambda: apps[0].db.is_dedicated_active)
    print("Dedicated database provisioned and configured {}".format(ip0))
    command_set1 = ('ap', '', opt, '1', '2', '1', 'y') + port + ('', '', pwd,
        TimedCommand(pwd, 360), '')
    apps[1].appliance_console.run_commands(command_set1)
    apps[1].evmserverd.wait_for_running()
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
@click.option('--provider-type', default='rhevm', help='Specify sprout provider type')
@click.option('--provider', default=None, help='Specify sprout provider, overrides provider_type')
@click.option('--lease', default='3h', help='set pool lease time, example: 1d4h30m')
@click.option('--sprout-poolid', default=None, help='Specify ID of existing pool')
@click.option('--desc', default='Replicated appliances', help='Set description of the pool')
@click.option('--remote-worker', is_flag=True, help='Add node to remote region')
def setup_replication_env(cfme_version, provider_type, provider, lease, sprout_poolid, desc,
                          remote_worker):
    lease_time = tot_time(lease)
    provider_type = None if provider else provider_type
    """Multi appliance setup with multi region and replication from remote to global"""
    required_app_count = 2
    sprout_client = SproutClient.from_config()

    if remote_worker:
        required_app_count += 1

    if sprout_poolid:
        if sprout_client.call_method('pool_exists', sprout_poolid):
            sprout_pool = sprout_client.call_method('request_check', sprout_poolid)
            if len(sprout_pool['appliances']) >= required_app_count:
                print("Processing pool...")
                apps = []
                for app in sprout_pool['appliances']:
                    apps.append(IPAppliance(app['ip_address']))
                sprout_client.set_pool_description(sprout_poolid, desc)
            else:
                sys.exit("Pool does not meet the minimum size requirements!")
        else:
            sys.exit("Pool not found!")

    else:
        print("Provisioning appliances")
        apps, request_id = provision_appliances(
            count=required_app_count, cfme_version=cfme_version,
            provider_type=provider_type, provider=provider, lease_time=lease_time
        )
        print("Appliance pool lease time is {}".format(lease))
        sprout_client.set_pool_description(request_id, desc)
        print("Appliances Provisioned")
    print("Configuring Replicated Environment")
    ip0 = apps[0].hostname
    ip1 = apps[1].hostname

    print("Global Appliance Configuration")
    opt = '5' if cfme_version >= "5.8" else '8'
    command_set0 = ('ap', '', opt, '1', '1', 'y', '1', 'n', '99', pwd,
        TimedCommand(pwd, 360), '')
    apps[0].appliance_console.run_commands(command_set0)
    apps[0].evmserverd.wait_for_running()
    apps[0].wait_for_web_ui()
    print("Done: Global @ {}".format(ip0))

    print("Remote Appliance Configuration")
    command_set1 = ('ap', '', opt, '2', ip0, '', pwd, '', '1', 'y', '1', 'n', '1', pwd,
        TimedCommand(pwd, 360), '')
    apps[1].appliance_console.run_commands(command_set1)
    apps[1].evmserverd.wait_for_running()
    apps[1].wait_for_web_ui()
    print("Done: Remote @ {}".format(ip1))

    if remote_worker:
        print("Remote Worker Appliance Configuration")
        ip2 = apps[2].hostname
        command_set2 = ['ap', '', opt, '2', ip1, '', pwd, '', '3', ip1, '', '', '', pwd, pwd]
        apps[2].appliance_console.run_commands(command_set2)
        apps[2].evmserverd.wait_for_running()
        apps[2].wait_for_web_ui()
        print("Done: Remote Worker @ {}".format(ip2))

    print("Configuring Replication")
    print("Setup - Replication on remote appliance")
    apps[1].set_pglogical_replication(replication_type=':remote')
    print("Setup - Replication on global appliance")
    apps[0].set_pglogical_replication(replication_type=':global')
    apps[0].add_pglogical_replication_subscription(apps[1].hostname)
    print("Done!")


@main.command('multi-region', help='Sets up replicated environment')
@click.option('--cfme-version', required=True)
@click.option('--provider-type', default='rhevm', help='Specify sprout provider type')
@click.option('--provider', default=None, help='Specify sprout provider, overrides provider_type')
@click.option('--lease', default='3d', help='set pool lease time, example: 1d4h30m')
@click.option('--sprout-poolid', default=None, help='Specify ID of existing pool')
@click.option('--desc', default='Replicated appliances', help='Set description of the pool')
@click.option('--remote-nodes', default=2, type=int, help='Add nodes to remote regions')
@click.option('--add-prov', default=None, type=str, multiple=True,
              help='Add providers to remote region appliances')
def setup_multiregion_env(cfme_version, provider_type, provider, lease, sprout_poolid, desc,
                          remote_nodes, add_prov):
    lease_time = tot_time(lease)
    provider_type = None if provider else provider_type
    """Multi appliance setup with multi region and replication from remote to global"""

    sprout_client = SproutClient.from_config()

    required_app_count = 1  # global app
    required_app_count += remote_nodes

    if sprout_poolid:
        if sprout_client.call_method('pool_exists', sprout_poolid):
            sprout_pool = sprout_client.call_method('request_check', sprout_poolid)
            if len(sprout_pool['appliances']) >= required_app_count:
                print("Processing pool...")
                apps = []
                for app in sprout_pool['appliances']:
                    apps.append(IPAppliance(app['ip_address']))
                sprout_client.set_pool_description(sprout_poolid, desc)
            else:
                sys.exit("Pool does not meet the minimum size requirements!")
        else:
            sys.exit("Pool not found!")

    else:
        print("Provisioning appliances")
        apps, request_id = provision_appliances(
            count=required_app_count, cfme_version=cfme_version,
            provider_type=provider_type, provider=provider, lease_time=lease_time
        )
        print("Appliance pool lease time is {}".format(lease))
        sprout_client.set_pool_description(request_id, desc)
        print("Appliances Provisioned")
    print("Configuring Replicated Environment")
    global_app = apps[0]
    gip = global_app.hostname

    remote_apps = apps[1:]

    print("Global Appliance Configuration")
    app_creds = {
        "username": credentials["database"]["username"],
        "password": credentials["database"]["password"],
        "sshlogin": credentials["ssh"]["username"],
        "sshpass": credentials["ssh"]["password"],
    }

    app_params = dict(region=99, dbhostname='localhost', username=app_creds['username'],
                      password=app_creds['password'], dbname='vmdb_production',
                      dbdisk=global_app.unpartitioned_disks[0])
    global_app.appliance_console_cli.configure_appliance_internal(**app_params)
    global_app.evmserverd.wait_for_running()
    global_app.wait_for_web_ui()

    print("Done: Global @ {}".format(gip))

    for num, app in enumerate(remote_apps):
        region_n = str((num + 1) * 10)
        print("Remote Appliance Configuration")
        app_params = dict(region=region_n,
                          dbhostname='localhost',
                          username=app_creds['username'],
                          password=app_creds['password'],
                          dbname='vmdb_production',
                          dbdisk=app.unpartitioned_disks[0],
                          fetch_key=gip,
                          sshlogin=app_creds['sshlogin'],
                          sshpass=app_creds['sshpass'])

        app.appliance_console_cli.configure_appliance_internal_fetch_key(**app_params)
        app.evmserverd.wait_for_running()
        app.wait_for_web_ui()
        print("Done: Remote @ {}, region: {}".format(app.hostname, region_n))

        print("Configuring Replication")
        print("Setup - Replication on remote appliance")
        app.set_pglogical_replication(replication_type=':remote')

    print("Setup - Replication on global appliance")
    global_app.set_pglogical_replication(replication_type=':global')
    for app in remote_apps:
        global_app.add_pglogical_replication_subscription(app.hostname)

    random.shuffle(remote_apps)
    if add_prov:
        for app, prov_id in zip(cycle(remote_apps), add_prov):
            stack.push(app)
            prov = get_crud(prov_id)
            print("Adding provider {} to appliance {}".format(prov_id, app.hostname))
            prov.create_rest()
            stack.pop()

    print("Done!")


if __name__ == "__main__":
    main()
