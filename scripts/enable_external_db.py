#!/usr/bin/env python2

"""Set up an external DB on an appliance over SSH.

Appliance address and database address are required.

Database name and region are optional and default to 'vmdb_production' and 0 respectively.
Credentials are optional but default values must be set in credentials.yaml under 'database' key.

Example usage:
  Connect appliance 10.0.0.1 to database 'cfme_db' on 20.0.0.1,
  use region 1 and default credentials (from yaml):

    enable_external_db.py 10.0.0.1 20.0.0.1 --database cfme_db --region 1
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
    parser.add_argument('db_address',
        help='hostname or ip address of external database')
    parser.add_argument('--database', default='vmdb_production',
        help='name of the external database')
    parser.add_argument('--region', default=0, type=int,
        help='region to assign to the new DB')
    parser.add_argument('--username', default=credentials['database']['username'],
        help='username for external database')
    parser.add_argument('--password', default=credentials['database']['password'],
        help='password for external database')

    args = parser.parse_args()

    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }
    rbt_repl = {
        'miq_lib': '/var/www/miq/lib',
        'host': args.db_address,
        'database': args.database,
        'region': args.region,
        'username': args.username,
        'password': args.password
    }

    # Find and load our rb template with replacements
    base_path = os.path.dirname(__file__)
    rbt = datafile.data_path_for_filename(
        'enable-external-db.rbt', base_path)
    rb = datafile.load_data_file(rbt, rbt_repl)

    # Init SSH client and sent rb file over to /tmp
    remote_file = '/tmp/%s' % generate_random_string()
    client = SSHClient(**ssh_kwargs)
    client.put_file(rb.name, remote_file)

    # Run the rb script, clean it up when done
    print 'Initializing Appliance External DB'
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
