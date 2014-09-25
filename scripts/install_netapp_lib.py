#!/usr/bin/env python2

"""SSH into a running appliance and install Netapp SDK
"""

import argparse
import sys
import time
import os
from urlparse import urlparse
from utils.conf import cfme_data, credentials, env
from utils.db import get_yaml_config, set_yaml_config
from utils.ssh import SSHClient


def parse_if_not_none(o):
    if o is None:
        return None
    return urlparse(o).netloc


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--address',
        help='hostname or ip address of target appliance',
        default=parse_if_not_none(env.get("base_url", None)))
    parser.add_argument(
        '--sdk_url',
        help='url to download sdk pkg',
        default=cfme_data.get("basic_info", {}).get("netapp_sdk_url", None))
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
    status, out = client.run_command('wget {url} -O {file} > /root/unzip.out 2>&1'.format(
        url=args.sdk_url, file=filename))

    # extract
    print 'Extracting sdk ({})'.format(filename)
    status, out = client.run_command('unzip -o -d /var/www/miq/vmdb/lib/ {}'.format(filename))
    if status != 0:
        print out
        sys.exit(1)

    # install
    print 'Installing sdk ({})'.format(foldername)
    path = "/var/www/miq/vmdb/lib/{}/lib/linux-64".format(foldername)
    # Check if we haven't already added this line
    if client.run_command("grep -F '{}' /etc/default/evm".format(path))[0] != 0:
        status, out = client.run_command(
            'echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:{}" >> /etc/default/evm'.format(path))
        if status != 0:
            print 'SDK installation failure (rc: {})'.format(out)
            print out
            sys.exit(1)
    else:
        print "Not needed to install, already done"

    print "Running ldconfig"
    client.run_command("ldconfig")

    print "Modifying YAML configuration"
    yaml = get_yaml_config("vmdb")
    yaml["product"]["storage"] = True
    set_yaml_config("vmdb", yaml)

    client.run_command("touch /var/www/miq/vmdb/HAS_NETAPP")  # To mark that we installed netapp

    # service evmserverd restart
    if args.restart:
        print 'Appliance restart'
        status, out = client.run_command('reboot &')
        time.sleep(30)  # To prevent clobbing with appliance shutting down
        print 'evmserverd restarted, the UI should start shortly.'
    else:
        print 'evmserverd must be restarted before netapp sdk can be used'


if __name__ == '__main__':
    sys.exit(main())
