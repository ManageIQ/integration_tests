#!/usr/bin/env python3
"""Collect artifacts after jenkins run
"""
import argparse
import sys

from cfme.utils.conf import credentials
from cfme.utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')

    args = parser.parse_args()

    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }

    # Init SSH client
    with SSHClient(**ssh_kwargs) as ssh_client:
        # generate installed rpm list
        ssh_client.run_command('rpm -qa | sort > /tmp/installed_rpms.txt')
        ssh_client.get_file('/tmp/installed_rpms.txt', 'installed_rpms.txt')

        # compress logs dir
        ssh_client.run_command('cd /var/www/miq/vmdb; tar zcf /tmp/appliance_logs.tgz log')
        ssh_client.get_file('/tmp/appliance_logs.tgz', 'appliance_logs.tgz')


if __name__ == '__main__':
    sys.exit(main())
