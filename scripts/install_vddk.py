#!/usr/bin/env python2

"""SSH into a running appliance and install VMware VDDK.
"""

import argparse
import sys
from utils.conf import credentials
from utils.ssh import SSHClient
from utils.wait import wait_for


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')
    parser.add_argument('vddk_url', help='url to download vddk pkg')
    parser.add_argument('--reboot', help='reboot after installation ' +
                        '(required for proper operation)', action="store_true")
    parser.add_argument('--force',
                        help='force installation if version detected', action="store_true")

    args = parser.parse_args()

    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }

    # Init SSH client
    client = SSHClient(**ssh_kwargs)

    # Get some particulars
    is_52 = '5.2' in client.get_version()
    is_already_installed = False
    if client.run_command('test -d /usr/lib/vmware-vix-disklib/lib64')[0] == 0:
        is_already_installed = True

    if not is_already_installed or args.force:

        # start
        filename = args.vddk_url.split('/')[-1]

        # download
        print 'Downloading vddk'
        # status, out = client.run_command('wget %s' % args.vddk_url)
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

        # 5.2 workaround
        if is_52:
            # find the vixdisk libs and add it to cfme 5.2 lib path which was hard coded for
            #    vddk v2.1 and v5.1
            print 'WARN: Adding 5.2 workaround'
            status, out = client.run_command("find /usr/lib/vmware-vix-disklib/lib64 -maxdepth 1" +
                                             " -type f -exec ls -d {} + | grep libvixDiskLib")
            for file in str(out).split("\n"):
                client.run_command("cd /var/www/miq/lib/VixDiskLib/vddklib; ln -s " + file)

        # reboot
        if args.reboot:
            print 'Appliance reboot'
            old_uptime = client.uptime()
            status, out = client.run_command('reboot')
            wait_for(lambda: client.uptime() < old_uptime, handle_exception=True, num_sec=300,
                     message='appliance to reboot', delay=10)
        else:
            print 'A reboot is required before vddk will work'


if __name__ == '__main__':
    sys.exit(main())
