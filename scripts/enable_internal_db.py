#!/usr/bin/env python

"""
SSH in to a running appliance and set up an internal DB

An optional region can be specified (default 0), and the script
will use the first available unpartitioned disk as the data volume
for postgresql.

"""

import argparse
import os
import sys

from common.randomness import generate_random_string
from common.ssh import SSHClient
from utils import datafile
from utils.credentials import load_credentials


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address',
        help='hostname or ip address of target appliance')
    parser.add_argument('--region', default=0, type=int,
        help='region to assign to the new DB')

    args = parser.parse_args()

    credentials = load_credentials()
    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }
    rbt_repl = {
        'miq_lib': '/var/www/miq/lib',
        'region': args.region
    }

    # Find and load our rb template with replacements
    base_path = os.path.dirname(__file__)
    rbt = datafile.data_path_for_filename(
        'enable-internal-db.rbt', base_path)
    rb = datafile.load_data_file(rbt, rbt_repl)

    # Init SSH client and sent rb file over to /tmp
    remote_file = '/tmp/%s' % generate_random_string()
    client = SSHClient(**ssh_kwargs)
    client.put_file(rb.name, remote_file)

    # Run the rb script, clean it up when done
    print 'Initializing Appliance Internal DB'
    status, out = client.run_command('ruby %s' % remote_file)
    client.run_command('rm %s' % remote_file)
    if status != 0:
        print 'Enabling DB failed with error:'
        print out
        sys.exit(1)

    # set up the DB region, reboot
    print 'Setting up DB with region %s' % args.region
    status, out = client.run_rake_command(
        'evm:db:region -- --region %s' % args.region)
    if status != 0:
        print 'DB polutation failed with error:'
        print out
        sys.exit(1)
    else:
        print 'Rebooting appliance'
        client.run_command('reboot')


if __name__ == '__main__':
    sys.exit(main())
