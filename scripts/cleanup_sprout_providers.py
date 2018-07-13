#!/usr/bin/env python

# Script to audit and cleanup sprout providers
# Goal is to identify VM's running on the provider that are not reported by sprout's API
# These VMs are effectively orphaned, and should just be deleted
# NOTE: There's some inherent danger in running this, YMMV and use at your own risk
# TODO list pods on openshift too
import argparse
import re
import sys

from collections import namedtuple
from functools import partial
from miq_version import generic_matchers
from six.moves import input
from tabulate import tabulate

from cfme.test_framework.sprout.client import SproutClient
from cfme.utils.conf import cfme_data
from cfme.utils.path import log_path
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import get_mgmt
from cfme.utils.thread_tools import pool_manager

# log to stdout for CI simplicity
add_stdout_handler(logger)

ProvAppPair = namedtuple('ProvAppPair', ['prov_key', 'vm_name'])
simple_tab = partial(tabulate, headers=['Key', 'VM'], tablefmt='orgtbl')
sprout_matchers = [
    m
    for k, m in generic_matchers
    if k == 'sprout'] + [r'^jenkins_'] + [r'^dockerbot_'] + [r'.*_cfme_']


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('-f', '--force', default=False, action='store_true', dest='force',
                        help='Do not prompt before deleting VMs (danger zone!)')
    parser.add_argument('--provider', dest='providers', action='append', default=None,
                        help='Provider(s) to inspect, can be used multiple times. '
                             'Only allows sprout providers',
                        metavar='PROVIDER')
    parser.add_argument('--provider-type', dest='provider_type', default=None,
                        help='Provider type matching those used in cfme_data, to focus cleanup')
    parser.add_argument('--outfile', dest='outfile',
                        default=log_path.join('cleanup_sprout_providers.log').strpath,
                        help='outfile to list VMs and results')
    args = parser.parse_args()
    return args


def audit_providers(providers, provider_type, force, outfile):
    """Look for orphaned appliances on sprout providers
    1. Pull sprout list of appliances
    2. Organize by provider + name
    3. Pull provider VMs
    4. Identify VMs on provider that do not exist in sprout
    5. Purge the weak
    Args:
        providers: list of provider keys to check, or empty to hit all sprout providers
        force: boolean whether to force delete, or just print list of orphaned vms
        outfile: string path of the log file to write tabulated results to

    """
    mgmt_systems = cfme_data.get('management_systems')
    sprout_providers = []
    for key, value in mgmt_systems.items():
        if (value.get('use_for_sprout') and
                value.type != 'openshift' and
                ((provider_type and value.type == provider_type) or provider_type is None)):
            sprout_providers.append(key)
    if providers and any([k not in sprout_providers for k in providers]):
        logger.exception('Provider key given is not used by sprout according to yamls')
        return 1

    valid_providers = providers if providers else sprout_providers
    logger.info('List of providers to audit: %s', valid_providers)
    logger.info('List of matching VM names to audit: %s', sprout_matchers)

    # step 1 + 2
    logger.info('Scanning sprout API for appliances...')
    sprout_client = SproutClient.from_config()
    # fetch sprout appliances from shepherd
    unused = sprout_client.call_method('list_appliances', used=False)
    sprout_unused_appliances = [ProvAppPair(a['provider'], a['name'])
                                for a in unused
                                if a['provider'] in valid_providers]
    logger.info("Sprout shepherd appliances by provider: \n%s", simple_tab(sprout_unused_appliances))
    # fetch sprout appliances that were assigned
    used = sprout_client.call_method('list_appliances', used=True)
    sprout_used_appliances = [ProvAppPair(a['provider'], a['name'])
                              for a in used
                              if a['provider'] in valid_providers]
    logger.info("Sprout assigned appliances by provider: \n%s", simple_tab(sprout_used_appliances))

    all_sprout_apps = sprout_unused_appliances + sprout_used_appliances

    for prov_key in valid_providers:
        logger.info('Checking provider %s', prov_key)
        mgmt = get_mgmt(prov_key)
        try:
            mgmt_vms = [vm
                        for vm in mgmt.list_vms()
                        if any([re.search(matcher, vm.name) for matcher in sprout_matchers])]
        except Exception:
            logger.exception('Exception while checking provider %s', prov_key)
            continue
        logger.info('Provider %s VMs matching sprout names: \n%s',
                    prov_key, simple_tab({prov_key: mgmt_vms}))

        to_delete = []
        sprout_app_vms = [app.vm_name for app in all_sprout_apps if app.prov_key == prov_key]
        for mgmt_vm in mgmt_vms:
            if mgmt_vm.name not in sprout_app_vms:
                logger.info('Found name-matched VM "%s" on provider, NOT in sprout', mgmt_vm)
                to_delete.append(mgmt_vm)

        logger.warning('WILL DELETE \n%s', [v.name for v in to_delete])

        if to_delete and not force:
            yesno = input('Delete these VMs? [y/N]: ')
            if str(yesno).lower() != 'y':
                logger.info('Skipping cleanup on %s', prov_key)
                continue

        # delete either confirmed or force was true
        #pool_manager(func_list=[vm.cleanup for vm in to_delete])
        for vm_to_delete in to_delete:
            logger.warning('Deleting VM: %s', vm_to_delete)
            try:
                vm_to_delete.cleanup()
            except Exception:
                logger.exception('Exception while calling cleanup on %s', vm_to_delete)



if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(audit_providers(args.providers, args.provider_type, args.force, args.outfile))
