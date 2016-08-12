#!/usr/bin/env python2

"""Collect artifacts after jenkins run
"""

from __future__ import unicode_literals
import argparse
import sys
from utils.conf import credentials
from utils.ssh import SSHClient


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
    client = SSHClient(**ssh_kwargs)

    # generate installed rpm list
    status, out = client.run_command('rpm -qa | sort > /tmp/installed_rpms.txt')
    client.get_file('/tmp/installed_rpms.txt', 'installed_rpms.txt')

    # compress logs dir
    status, out = client.run_command('cd /var/www/miq/vmdb; tar zcvf /tmp/appliance_logs.tgz log')
    client.get_file('/tmp/appliance_logs.tgz', 'appliance_logs.tgz')


if __name__ == '__main__':
    sys.exit(main())
