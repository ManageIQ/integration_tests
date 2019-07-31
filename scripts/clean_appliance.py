#!/usr/bin/env python3
"""Clean out an appliance DB

In the case where an appliance has been used for a lot of testing and filled up with old records,
this script will clean out an appliance's database and wait for the UI to come back online.

By default, it will use the appliance named in conf.env, but can be explicitly aimed at another
appliance if needed.

This can take several minutes to run, but should be faster than provisioning a new appliance.

"""
import argparse
import subprocess
import sys

from cfme.utils.appliance import IPAppliance
from cfme.utils.conf import credentials
from cfme.utils.path import scripts_path
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for_decorator


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hostname', nargs='?', default=None,
                        help='hostname or ip address of target appliance')
    parser.add_argument('username', nargs='?', default=credentials['ssh']['username'],
                        help='SSH username for target appliance')
    parser.add_argument('password', nargs='?', default=credentials['ssh']['password'],
                        help='SSH password for target appliance')
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='Do not print output of SSH commnads')

    args = parser.parse_args()

    ssh_kwargs = {
        'username': args.username,
        'password': args.password
    }
    if args.hostname is not None:
        ssh_kwargs['hostname'] = args.hostname
        appliance = IPAppliance(args.hostname)
        if appliance.version < '5.9':
            # Running evm:db:reset on CFME 5.8 sometimes leaves it in a state
            # where it is unable to start again
            print('EXITING: This script does not work reliably for CFME 5.8')
            return 1

    with SSHClient(stream_output=not args.quiet, **ssh_kwargs) as ssh_client:
        # Graceful stop is done here even though it is slower than killing ruby processes.
        # Problem with killing ruby is that evm_watchdog gets spawned right after being killed
        # and then prevents you from destroying the DB.
        # Graceful stop makes sure there are no active connections to the DB left.
        print('Stopping evmserverd...')
        ssh_client.run_command('systemctl stop evmserverd')

        @wait_for_decorator(num_sec=60, delay=5)
        def check_no_db_connections():
            psql_cmd = '/opt/rh/rh-postgresql95/root/usr/bin/psql'
            query = 'SELECT numbackends FROM pg_stat_database WHERE datname = \'vmdb_production\''
            db = 'postgres'
            response = ssh_client.run_command('{} -c "{}" -d "{}" -t'.format(psql_cmd, query, db))
            db_connections = int(response.output.strip())
            return db_connections == 0

        ssh_client.run_rake_command('evm:db:reset', disable_db_check=True)
        ssh_client.run_command('systemctl start evmserverd')

        # SSHClient has the smarts to get our hostname if none was provided
        # Soon, utils.appliance.Appliance will be able to do all of this
        # and this will be made good
        hostname = ssh_client._connect_kwargs['hostname']

    print('Waiting for appliance UI...')
    args = [scripts_path.join('wait_for_appliance_ui.py').strpath, 'http://{}'.format(hostname)]
    return subprocess.call(args)


if __name__ == '__main__':
    sys.exit(main())
