#!/usr/bin/env python

"""SSH into a running appliance and install VMware VDDK.
"""

import argparse
import sys
from utils.conf import credentials
from utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')
    parser.add_argument('vddk_url', help='url to download vddk pkg')
    parser.add_argument('--reboot', help='reboot after installation ' +
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
    filename = args.vddk_url.split('/')[-1]

    # download
    print 'Downloading vddk'
    #status, out = client.run_command('wget %s' % args.vddk_url)
    status, out = client.run_command('curl %(url)s -o %(file)s' %
        {'url': args.vddk_url, 'file': filename})

    # extract
    print 'Extracting vddk'
    status, out = client.run_command('tar xvf %s' % filename)
    if status != 0:
        print "Error: unknown format"
        print out
        sys.exit(1)

    # install
    print 'Installing vddk'
    status, out = client.run_command('vmware-vix-disklib-distrib/vmware-install.pl ' +
        '--default EULA_AGREED=yes')
    if status != 0:
        print 'VDDK installation failure (rc:' + out + ')'
        print out
        sys.exit(1)
    else:
        status, out = client.run_command('ldconfig')

    # verify
    print 'Verifying vddk'
    status, out = client.run_command('ldconfig -p | grep vix')
    if len(out) < 2:
        print "Potential installation issue, libraries not detected"
        print out
        sys.exit(1)

    # reboot
    if args.reboot:
        print 'Appliance reboot'
        status, out = client.run_command('reboot')
        #print 'DB Enabled, evm watchdog should start the UI shortly.'
    else:
        print 'A reboot is required before vddk will work'


if __name__ == '__main__':
    sys.exit(main())
