#!/usr/bin/env python2

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

from cfme.utils.conf import credentials
from cfme.utils.path import scripts_path
from cfme.utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hostname', nargs='?', default=None,
                        help='hostname or ip address of target appliance')
    parser.add_argument('username', nargs='?', default=credentials['ssh']['username'],
                        help='SSH username for target appliance')
    parser.add_argument('password', nargs='?', default=credentials['ssh']['password'],
                        help='SSH password for target appliance')

    args = parser.parse_args()

    ssh_kwargs = {
        'username': args.username,
        'password': args.password
    }
    if args.hostname is not None:
        ssh_kwargs['hostname'] = args.hostname

    with SSHClient(stream_output=True, **ssh_kwargs) as ssh_client:

        # `systemctl stop evmserverd` is a little slow, and we're destroying the
        # db, so rudely killing ruby speeds things up significantly
        print('Stopping ruby processes...')
        ssh_client.run_command('killall ruby')
        ssh_client.run_rake_command('evm:db:reset')
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
