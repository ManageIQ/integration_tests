#!/usr/bin/env python2

import argparse
import sys

from mgmtsystem.ec2 import EC2System

from utils.conf import cfme_data
from utils.conf import credentials
from utils.providers import list_providers


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--region', default=None, dest='provider_region',
        help='name of the region to list the vms..')
    parser.add_argument('--provider_key', default=None,
        help='provider_key ad mentioned in the cfme_data to list the vms..')
    args = parser.parse_args()
    return args


def list_vms(provider_key=None, provider_region=None):
    for provider in list_providers('ec2'):
        if provider_key and provider != provider_key:
            continue
        provider_data = cfme_data['management_systems'][provider]
        provider_creds = provider_data['credentials']
        username = credentials[provider_creds]['username']
        password = credentials[provider_creds]['password']
        region = provider_data['region']
        if provider_region and region != provider_region:
            continue

        kwargs = {
            'username': username,
            'password': password,
            'region': region,
        }
        ec2 = EC2System(**kwargs)
        print("\n{}  {}:\n-----------------------".format(provider, region))
        ec2_vms = ec2.list_vm()
        if ec2_vms:
            for vm in ec2.list_vm():
                print(vm)
        else:
            print("No VM's created in this region\n")


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(list_vms(args.provider_key, args.provider_region))
