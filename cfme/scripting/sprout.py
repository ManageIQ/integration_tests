#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from __future__ import print_function

"""Script to checkout a sprout appliance

Usage:

   sprout.py checkout
"""
import click

import os
import signal
import sys
import time
import yaml

from cfme.test_framework.sprout.plugin import SproutManager, SproutProvisioningRequest
from cfme.utils.path import conf_path


@click.group(help='Functions for interacting with sprout')
def main():
    pass


@main.command('checkout', help='Checkout appliance and start keepalive daemon')
@click.option('--appliances', envvar="SPROUT_APPLIANCES", default=1,
              help='How many appliances to provision')
@click.option('--timeout', default=60, help='How many minutes is the lease timeout')
@click.option('--provision-timeout', default=60,
              help='How many minutes to wait for appliances provisioned')
@click.option('--group', required=True, envvar='SPROUT_GROUP', help='Which stream to use')
@click.option('--version', default=None, help='Which version to use')
@click.option('--date', default=None, help='Which date to use')
@click.option('--desc', default=None, envvar='SPROUT_DESC', help='Set description of the pool')
@click.option('--override-ram', default=0, help='Override RAM (MB). 0 means no override')
@click.option('--override-cpu', default=0,
              help='Override CPU core count. 0 means no override')
@click.option('--populate-yaml', is_flag=True, default=False,
              help="Populate the yaml with the appliance")
@click.option('--provider', default=None, help="Which provider to use")
def checkout(appliances, timeout, provision_timeout, group, version, date, desc,
             override_ram, override_cpu, populate_yaml, provider):
    """checks out a sprout provisioning request, and returns it on exit"""
    override_cpu = override_cpu or None
    override_ram = override_ram or None
    sr = SproutProvisioningRequest(group=group, count=appliances, version=version, date=date,
                                   lease_time=timeout, provision_timeout=provision_timeout,
                                   desc=desc, cpu=override_cpu, ram=override_ram, provider=provider)
    print(sr)
    sm = SproutManager()

    def exit_gracefully(signum, frame):
        sm.destroy_pool()
        sys.exit(0)

    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
    try:
        appliance_data = sm.request_appliances(sr)
        while not sm.check_fullfilled():
            print("waiting...")
            time.sleep(10)
        sm.reset_timer()
        for app in appliance_data:
            print("{}: {}".format(app['name'], app['ip_address']))
        if populate_yaml:
            populate_config_from_appliances(appliance_data)
        print("Appliance checked out, hit ctrl+c to checkin")

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        try:
            sm.destroy_pool()
        except:
            print("Error in pool destroy")


def populate_config_from_appliances(appliance_data):
    """populates env.local.yaml with the appliances just obtained

    args:
        appliance_data: the data of the appliances as taken from sprout
    """
    file_name = conf_path.join('env.local.yaml').strpath
    if os.path.exists(file_name):
        with open(file_name) as f:
            y_data = yaml.load(f)
        if not y_data:
            y_data = {}
    else:
        y_data = {}
    if y_data:
        with open(conf_path.join('env.local.backup').strpath, 'w') as f:
            yaml.dump(y_data, f, default_flow_style=False)

    y_data['appliances'] = []
    for app in appliance_data:
        y_data['appliances'].append({'base_url': 'https://{}/'.format(app['ip_address'])})
    with open(file_name, 'w') as f:
        try:
            del y_data['base_url']
        except KeyError:
            pass
        yaml.dump(y_data, f, default_flow_style=False)


if __name__ == "__main__":
    main()
