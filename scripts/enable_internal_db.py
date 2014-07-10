#!/usr/bin/env python2

"""SSH in to a running appliance and set up an internal DB.

An optional region can be specified (default 0), and the script
will use the first available unpartitioned disk as the data volume
for postgresql.

Running this script against an already configured appliance is
unsupported, hilarity may ensue.

"""

import argparse
import os
import sys

from utils import datafile
from utils.conf import credentials
from utils.randomness import generate_random_string
from utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address',
        help='hostname or ip address of target appliance')
    parser.add_argument('--region', default=0, type=int,
        help='region to assign to the new DB')

    args = parser.parse_args()

    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }
    client = SSHClient(**ssh_kwargs)
    print 'Initializing Appliance Internal DB'

    if client.run_command('ls -l /bin/appliance_console_cli')[0] == 0:
        status, out = client.run_command('appliance_console_cli --ca --region 1 --internal')
        if status != 0:
            print 'Enabling DB failed with error:'
            print out
            sys.exit(1)
        else:
            print 'DB Enabled, evm watchdog should start the UI shortly.'
    else:
        rbt_repl = {
            'miq_lib': '/var/www/miq/lib',
            'region': args.region
        }

        # Find and load our rb template with replacements
        base_path = os.path.dirname(__file__)
        rbt = datafile.data_path_for_filename(
            'enable-internal-db.rbt', base_path)
        rb = datafile.load_data_file(rbt, rbt_repl)

        # sent rb file over to /tmp
        remote_file = '/tmp/%s' % generate_random_string()
        client.put_file(rb.name, remote_file)

        # Run the rb script, clean it up when done
        status, out = client.run_command('ruby %s' % remote_file)
        client.run_command('rm %s' % remote_file)
        if status != 0:
            print 'Enabling DB failed with error:'
            print out
            sys.exit(1)
        else:
            print 'DB Enabled, evm watchdog should start the UI shortly.'


if __name__ == '__main__':
    sys.exit(main())
