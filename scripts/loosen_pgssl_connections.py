#!/usr/bin/env python2

"""SSH into a running appliance and loosen postgres connections (temporary workaround).
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
    client = SSHClient(**ssh_kwargs)

    # set root password
    client.run_command("psql -d vmdb_production -c \"alter user " +
        credentials['database']['username'] + " with password '" +
        credentials['database']['password'] + "'\"")

    # back up pg_hba.conf
    client.run_command('mv /opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf ' +
        '/opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf.sav')

    # rewrite pg_hba.conf
    client.run_command("echo 'local all postgres,root trust' > " +
        "/opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf")
    client.run_command("echo 'host all all 0.0.0.0/0 md5' >> " +
        "/opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf")
    client.run_command("echo 'hostssl all all all cert map=sslmap' >> " +
        "/opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf")
    client.run_command("chown postgres:postgres " +
        "/opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf")

    # restart postgres
    client.run_command("service postgresql92-postgresql restart")


if __name__ == '__main__':
    sys.exit(main())
