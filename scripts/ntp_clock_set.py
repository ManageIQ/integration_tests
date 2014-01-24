#!/usr/bin/env python2
# -*- coding: utf-8 -*-

""" Set correct time via NTP

This script prevents failing of the tests with sudden time update from NTP.
It forces an immediate update of the time bringing it to the correct one.
Therefore the "Session timeout" error cannot happen when the CFME watchdog's ntp update comes.
Requires this in conf/cfme_data.yaml

clock_servers:
- server1.org
- server2.org
...
- serverN.org
"""

import argparse
from utils.conf import credentials, cfme_data
from utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'address',
        help='hostname or ip address of target appliance'
    )
    args = parser.parse_args()
    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }
    with SSHClient(**ssh_kwargs) as ssh:
        print("Setting appliance's time. Please wait.")
        servers_str = " ".join(["'%s'" % server for server in cfme_data["clock_servers"]])
        status, out = ssh.run_command("ntpdate " + servers_str)
        if status != 0:
            print("Could not set the time. Check the output of the command, please:")
            print(out.strip())
            return 1

        print("Time was set. Now it should be safe to log in and test on the appliance.")
        return 0


if __name__ == "__main__":
    exit(main())
