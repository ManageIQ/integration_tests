#!/usr/bin/env python3
"""SSH into a running appliance and install SNMP listener."""
import argparse
import sys

import requests

from cfme.utils.conf import credentials
from cfme.utils.path import scripts_data_path
from cfme.utils.ssh import SSHClient


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
    with SSHClient(**ssh_kwargs) as ssh_client:

        snmp_path = scripts_data_path.join("snmp")

        # Copy
        print("Copying files")
        ssh_client.put_file(snmp_path.join("snmp_listen.rb").strpath, "/root/snmp_listen.rb")
        ssh_client.put_file(snmp_path.join("snmp_listen.sh").strpath, "/root/snmp_listen.sh")

        # Enable after startup
        print("Enabling after startup")
        result = ssh_client.run_command("grep 'snmp_listen[.]sh' /etc/rc.local")
        if result.failed:
            ssh_client.run_command("echo 'cd /root/ && ./snmp_listen.sh start' >> /etc/rc.local")
        assert ssh_client.run_command("grep 'snmp_listen[.]sh' /etc/rc.local").success, (
            "Could not enable!")

        # Run!
        print("Starting listener")
        assert ssh_client.run_command("cd /root/ && ./snmp_listen.sh start").success, (
            "Could not start!")

        # Open the port if not opened
        print("Opening the port in iptables")
        result = ssh_client.run_command("grep '--dport 8765' /etc/sysconfig/iptables")
        if result.failed:
            # append after the 5432 entry
            ssh_client.run_command(
                "sed -i '/--dport 5432/a -A INPUT -p tcp -m tcp --dport 8765 -j ACCEPT' "
                "/etc/sysconfig/iptables"
            )
            ssh_client.run_command("systemctl restart iptables")
            # last ssh command, close
            # Check if accessible
            try:
                requests.get(f"http://{args.address}:8765/")
            except requests.exceptions.ConnectionError:
                print("Could not detect running listener!")
                exit(2)


if __name__ == '__main__':
    sys.exit(main())
