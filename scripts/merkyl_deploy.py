#!/bin/env python2

import argparse
import os.path
import sys

from utils.conf import credentials
from utils import ssh
from utils.path import data_path


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hostname', nargs='?', default=None,
        help='hostname or ip address of target appliance')
    parser.add_argument('username', nargs='?', default=credentials['ssh']['username'],
        help='SSH username for target appliance')
    parser.add_argument('password', nargs='?', default=credentials['ssh']['password'],
        help='SSH password for target appliance')
    parser.add_argument('start', action="store_true", default=False, help='Start Merkyl?')

    args = parser.parse_args()

    ssh_kwargs = {
        'username': args.username,
        'password': args.password
    }
    if args.hostname is not None:
        ssh_kwargs['hostname'] = args.hostname

    client = ssh.SSHClient(stream_output=True, **ssh_kwargs)

    client.run_command('mkdir -p /root/merkyl')
    for filename in ['__init__.py', 'merkyl.tpl', ('bottle.py.dontflake', 'bottle.py'),
                     'allowed.files']:
        if isinstance(filename, basestring):
            src = dest = filename
        else:
            src, dest = filename
        client.put_file(os.path.join(data_path.strpath, 'bundles', 'merkyl', src),
                        os.path.join('/root/merkyl', dest))
    client.put_file(os.path.join(data_path.strpath, 'bundles', 'merkyl', 'merkyl'),
                    os.path.join('/etc/init.d/merkyl'))
    client.run_command('chmod 775 /etc/init.d/merkyl')
    client.run_command(
        '/bin/bash -c \'if ! [[ $(iptables -L -n | grep "state NEW tcp dpt:8192") ]];'
        ' then iptables -I INPUT 6 -m state'
        ' --state NEW -m tcp -p tcp --dport 8192 -j ACCEPT; fi\'')
    if args.start:
        client.run_command('service merkyl restart')

if __name__ == '__main__':
    sys.exit(main())
