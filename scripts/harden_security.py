#!/usr/bin/env python2

"""SSH into a running appliance and configure security.

Configures security on appliance(s) according to this document:
https://access.redhat.com/articles/1124753

Works for single appliance and distributed appliance configurations.
In distributed configurations, provide the hostname of the replication
parent first, and then provide the hostnames of any child appliances using
the '-c' flag.

Example usage:
  Configure security for a single appliance:

   configure_security.py 10.0.0.1

  Configure security for distributed appliance set:

   # replication parent: 10.0.0.1
   # replication child: 10.0.0.2
   # replication child: 10.0.0.3
   configure_security.py 10.0.0.1 -c 10.0.0.2 -c 10.0.0.3

"""

from __future__ import unicode_literals
import argparse
import fauxfactory
import re
import socket
import sys

from utils.conf import credentials
from utils.ssh import SSHClient
from utils.wait import wait_for


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('appliance',
        help='hostname or ip address of parent appliance')
    parser.add_argument('-c', action='append', dest='children',
        help='hostname or ip address of child appliance')
    args = parser.parse_args()
    print("Appliance: {}".format(args.appliance))
    if args.children:
        for child in args.children:
            print("Child: {}".format(child))

    local_key_name = "v2_key_" + fauxfactory.gen_alphanumeric(8)

    ssh_creds = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
    }

    def is_ssh_running(address):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex((address, 22))
        return result == 0

    def generate_key(address):
        with SSHClient(hostname=address, **ssh_creds) as client:
            print('Connecting to Appliance...')
            status, out = client.run_command(
                'ruby /var/www/miq/vmdb/tools/fix_auth.rb --key --verbose')
            if status != 0:
                print('Creating new encryption key failed.')
                print(out)
                sys.exit(1)
            else:
                print('New encryption key created.')
                if args.children:
                    # Only copy locally if needed for child appliances
                    client.get_file('/var/www/miq/vmdb/certs/v2_key',
                                    local_key_name)

    def update_db_yaml(address):
        with SSHClient(hostname=address, **ssh_creds) as client:
            client.run_command('cd /var/www/miq/vmdb')
            status, out = client.run_rails_command(
                '\'puts MiqPassword.encrypt("smartvm");\'')
            if status != 0:
                print('Retrieving encrypted db password failed on {}'.format(address))
                sys.exit(1)
            else:
                encrypted_pass = out
                status, out = client.run_command(
                    ('cd /var/www/miq/vmdb; '
                     'sed -i.`date +%m-%d-%Y` "s/password:'
                     ' .*/password: {}/g" config/database.yml'.format(re.escape(encrypted_pass))))
                if status != 0:
                    print('Updating database.yml failed on {}'.format(address))
                    print(out)
                    sys.exit(1)
                else:
                    print('Updating database.yml succeeded on {}'.format(address))

    def update_password(address):
        with SSHClient(hostname=address, **ssh_creds) as client:
            status, out = client.run_command(
                'ruby /var/www/miq/vmdb/tools/fix_auth.rb --hostname localhost --password smartvm')
            if status != 0:
                print('Updating DB password failed on {}'.format(address))
                print(out)
                sys.exit(1)
            else:
                print('DB password updated on {}'.format(address))

    def put_key(address):
        print('copying key to {}'.format(address))
        with SSHClient(hostname=address, **ssh_creds) as client:
            client.put_file(local_key_name, '/var/www/miq/vmdb/certs/v2_key')

    def restart_appliance(address):
        print('Restarting evmserverd on {}'.format(address))
        with SSHClient(hostname=address, **ssh_creds) as client:
            status, out = client.run_command('service evmserverd restart')
            if status != 0:
                print("Restarting evmserverd failed on {}".format(address))
                sys.exit(1)
            else:
                print("Restarting succeeded on {}".format(address))

    # make sure ssh is ready on each appliance
    wait_for(func=is_ssh_running, func_args=[args.appliance], delay=10, num_sec=600)

    # generate key on master appliance
    generate_key(args.appliance)
    update_db_yaml(args.appliance)

    # copy to other appliances
    if args.children:
        for child in args.children:
            wait_for(func=is_ssh_running, func_args=[child], delay=10, num_sec=600)
            put_key(child)
            update_db_yaml(child)

    # restart master appliance (and children, if provided)
    restart_appliance(args.appliance)
    if args.children:
        for child in args.children:
            restart_appliance(child)
    print("Appliance(s) restarted with new key in place.")

    # update encrypted passwords in each database-owning appliance.

    update_password(args.appliance)
    if args.children:
        for child in args.children:
            update_password(child)

    # Restart again!
    restart_appliance(args.appliance)
    if args.children:
        for child in args.children:
            restart_appliance(child)

    print("Done!")


if __name__ == '__main__':
    sys.exit(main())
