#!/usr/bin/env python2

"""SSH into a running appliance and install Netapp SDK
"""

import argparse
import sys
import os
from utils.conf import credentials
from utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')
    parser.add_argument('sdk_url', help='url to download sdk pkg')
    parser.add_argument('--restart', help='restart evmserverd after installation ' +
        '(required for proper operation)', action="store_true")

    args = parser.parse_args()

    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }

    # Init SSH client
    client = SSHClient(**ssh_kwargs)

    # start
    filename = args.sdk_url.split('/')[-1]
    foldername = os.path.splitext(filename)[0]

    # download
    print 'Downloading sdk'
    status, out = client.run_command('curl %(url)s -o %(file)s > /root/unzip.out 2>&1' %
        {'url': args.sdk_url, 'file': filename})

    # extract
    print 'Extracting sdk (' + filename + ')'
    status, out = client.run_command('unzip -o -f -d /var/www/miq/vmdb/lib/ %s' % filename)
    if status != 0:
        print out
        sys.exit(1)

    # install
    print 'Installing sdk (' + foldername + ')'
    status, out = client.run_command('echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:' +
        '/var/www/miq/vmdb/lib/' + foldername + '/lib/linux-64" >> /etc/default/evm')
    if status != 0:
        print 'SDK installation failure (rc:' + out + ')'
        print out
        sys.exit(1)

    # service evmserverd restart
    if args.restart:
        print 'Appliance restart'
        status, out = client.run_command('service evmserverd restart')
        print 'evmserverd restarted, the UI should start shortly.'
    else:
        print 'evmserverd must be restarted before netapp sdk can be used'


if __name__ == '__main__':
    sys.exit(main())
