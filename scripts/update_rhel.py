#!/usr/bin/env python2

"""Run yum updates against a given repo
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
    parser.add_argument("-u", "--url", action="append", help="url(s) to use for update")
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
    repo_file_contents = ""
    for i, url in enumerate(args.url):
        repo_file_contents += "[update-" + str(i) + "]\nname=update-url-" + str(i) + \
            "\nbaseurl=" + url + "\nenabled=1\ngpgcheck=0\n\n"

    # create repo file on appliance
    print 'Create update repo file'
    status, out = client.run_command(
        'echo "%s" >/etc/yum.repos.d/updates.repo' % repo_file_contents)

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
        old_uptime = client.uptime()
        status, out = client.run_command('reboot')
        wait_for(lambda: client.uptime() < old_uptime, handle_exception=True, num_sec=300,
                 message='appliance to reboot', delay=10)
    else:
        print 'A reboot is recommended.'


if __name__ == '__main__':
    sys.exit(main())
