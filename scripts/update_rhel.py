#!/usr/bin/env python

"""Run yum updates against a given repo
"""

import argparse
import sys
from utils.conf import credentials
from utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')
    parser.add_argument('repo_url', help='updates base url')
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

    # create repo file
    repo_file = "[rhel-updates]\nname=rhel6-updates\nbaseurl=" + args.repo_url + "\nenabled=1\ngpgcheck=0"

    # create repo file on appliance
    print 'Create update repo file'
    status, out = client.run_command('echo "%s" >/etc/yum.repos.d/rhel_updates.repo' % repo_file)

    # update
    print 'Running rhel updates...'
    status, out = client.run_command('yum update -y --nogpgcheck')
    print "\n" + out + "\n"
    if status != 0:
        print "ERROR during update"
        sys.exit(1)


    # reboot
    if args.reboot:
        print 'Appliance reboot'
        status, out = client.run_command('reboot')
    else:
        print 'A reboot is recommended.'


if __name__ == '__main__':
    sys.exit(main())
