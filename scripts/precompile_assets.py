#!/usr/bin/env python2

"""SSH into a running appliance and compile ui assets.
"""

import argparse
import sys
from utils.conf import credentials
from utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance',
        nargs='?', default=None)

    args = parser.parse_args()

    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
    }
    if args.address:
        ssh_kwargs['hostname'] = args.address

    # Init SSH client
    ssh_client = SSHClient(**ssh_kwargs)

    # compile assets if required (not required on 5.2)
    if not ssh_client.get_version().startswith("5.2"):
        ssh_client.run_rake_command("assets:precompile")
        ssh_client.run_rake_command("evm:restart")

    print "CFME UI worker restarted, UI should be available shortly"

if __name__ == '__main__':
    sys.exit(main())
