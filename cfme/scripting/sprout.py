#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""
import click
import signal
import time
import sys
# import yaml

from cfme.test_framework.sprout.plugin import SproutManager, SproutProvisioningRequest
# from utils.path import conf_path


@click.group(help='Functions for interacting with sprout')
def main():
    pass


@main.command('checkout', help='Checkout appliance and start keepalive daemon')
@click.option('--appliances', default=1, help='How many appliances to provision')
@click.option('--timeout', default=60, help='How many minutes is the lease timeout')
@click.option('--provision-timeout', default=60,
              help='How many minutes to wait for appliances provisioned')
@click.option('--group', default=None, help='Which stream to use')
@click.option('--version', default=None, help='Which version to use')
@click.option('--date', default=None, help='Which date to use')
@click.option('--desc', default=None, help='Set description of the pool')
@click.option('--override-ram', default=0, help='Override RAM (MB). 0 means no override')
@click.option('--override-cpu', default=0,
              help='Override CPU core count. 0 means no override')
@click.option('--populate-yaml', default=False, help="Populate the yaml with the appliance")
def checkout(appliances, timeout, provision_timeout, group, version, date, desc,
             override_ram, override_cpu, populate_yaml):
    """Function to show the given credentials, takes either a provider key or a credential key"""
    override_cpu = override_cpu or None
    override_ram = override_ram or None
    sr = SproutProvisioningRequest(group=group, count=appliances, version=version, date=date,
                                   lease_time=timeout, provision_timeout=provision_timeout,
                                   desc=desc, cpu=override_cpu, ram=override_ram)
    sm = SproutManager()

    def exit_gracefully(signum, frame):
        sm.destroy_pool()
        sys.exit(0)

    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
    try:
        sm.request_appliances(sr)
        while not sm.check_fullfilled():
            print("waiting...")
            time.sleep(10)

        # TODO - populate yaml
        print("Appliance checked out, hit ctrl+c to checkin")

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        try:
            sm.destroy_pool()
        except:
            print("Error in pool destroy")


if __name__ == "__main__":
    main()
