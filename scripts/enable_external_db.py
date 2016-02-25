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
import sys

from utils.appliance import IPAppliance
from utils.conf import credentials


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', nargs='?', default=None,
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

    print('Initializing Appliance External DB')
    ip_a = IPAppliance(args.address)
    status, out = ip_a.enable_external_db(args.db_address, args.region, args.database,
        args.username, args.password)

    if status != 0:
        print('Enabling DB failed with error:')
        print(out)
        sys.exit(1)
    else:
        print('DB Enabled, evm watchdog should start the UI shortly.')


if __name__ == '__main__':
    sys.exit(main())
