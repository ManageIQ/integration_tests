#!/usr/bin/env python2

"""SSH into a running appliance and install SNMP listener."""

from __future__ import unicode_literals
import argparse
import requests
import sys

from utils.conf import credentials
from utils.path import scripts_data_path
from utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')

    args = parser.parse_args()

    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }

    # Init SSH client
    client = SSHClient(**ssh_kwargs)

    snmp_path = scripts_data_path.join("snmp")

    # Copy
    print("Copying files")
    client.put_file(snmp_path.join("snmp_listen.rb").strpath, "/root/snmp_listen.rb")
    client.put_file(snmp_path.join("snmp_listen.sh").strpath, "/root/snmp_listen.sh")

    # Enable after startup
    print("Enabling after startup")
    status = client.run_command("grep 'snmp_listen[.]sh' /etc/rc.local")[0]
    if status != 0:
        client.run_command("echo 'cd /root/ && ./snmp_listen.sh start' >> /etc/rc.local")
    assert client.run_command("grep 'snmp_listen[.]sh' /etc/rc.local")[0] == 0, "Could not enable!"

    # Run!
    print("Starting listener")
    assert client.run_command("cd /root/ && ./snmp_listen.sh start")[0] == 0, "Could not start!"

    # Open the port if not opened
    print("Opening the port in iptables")
    status = client.run_command("grep '--dport 8765' /etc/sysconfig/iptables")[0]
    if status != 0:
        # append after the 5432 entry
        client.run_command(
            "sed -i '/--dport 5432/a -A INPUT -p tcp -m tcp --dport 8765 -j ACCEPT' "
            "/etc/sysconfig/iptables"
        )
        client.run_command("service iptables restart")
        # Check if accessible
        try:
            requests.get("http://{}:8765/".format(args.address))
        except requests.exceptions.ConnectionError:
            print("Could not detect running listener!")
            exit(2)


if __name__ == '__main__':
    sys.exit(main())
