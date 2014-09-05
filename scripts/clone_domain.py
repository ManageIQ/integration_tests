#!/usr/bin/env python2

"""Clone an Automate Domain

eg, clone_domain.py xx.xx.xx.xx ManageIQ Default

This can take several minutes to run.

"""
import argparse
import sys

from utils.conf import credentials
from utils.ssh import SSHClient
from utils.wait import wait_for


def is_database_ready(client):
    ec, out = client.run_command('psql -U postgres -t  -c "select now()" postgres')
    if ec == 0:
        return True
    else:
        return False


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hostname', nargs='?', default=None,
        help='hostname or ip address of target appliance')
    parser.add_argument('source', nargs='?', default='ManageIQ',
        help='Source Domain name')
    parser.add_argument('dest', nargs='?', default='Default',
        help='Destination Domain name')
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

    client = SSHClient(stream_output=True, **ssh_kwargs)

    # Make sure the database is ready
    wait_for(is_database_ready, func_args=[client])

    # Make sure the working dir exists
    client.run_command('mkdir -p /tmp/miq')
    print 'Exporting domain...'
    export_opts = 'DOMAIN={} EXPORT_DIR=/tmp/miq PREVIEW=false OVERWRITE=true'.format(args.source)
    export_cmd = 'evm:automate:export {}'.format(export_opts)
    print export_cmd
    client.run_rake_command(export_cmd)
    ro_fix_cmd = "sed -i 's/system: true/system: false/g' /tmp/miq/ManageIQ/__domain__.yaml"
    client.run_command(ro_fix_cmd)
    import_opts = 'DOMAIN={} IMPORT_DIR=/tmp/miq PREVIEW=false'.format(args.source)
    import_opts += ' OVERWRITE=true IMPORT_AS={}'.format(args.dest)
    import_cmd = 'evm:automate:import {}'.format(import_opts)
    print import_cmd
    client.run_rake_command(import_cmd)


if __name__ == '__main__':
    sys.exit(main())
