#!/usr/bin/env python3
import argparse
import re
import sys

from cfme.containers.provider.openshift import OpenshiftProvider
from cfme.utils.appliance import DummyAppliance
from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.providers import list_providers
from cfme.utils.providers import ProviderFilter

add_stdout_handler(logger)

global_scc_names = ['anyuid', 'privileged']

default_namespace_regex = ['^.*?-project-',
                           '^jenkins-.*',
                           '^.*?s-appl-',
                           '^test',
                           '^long-test',
                           '^external-test']


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('-s', '--cleanup-scc', action='store_true',
                        help="removes openshift sa from system scc which no longer belong to any "
                             "appliance project")
    parser.add_argument('text_to_match', nargs='*', default=default_namespace_regex,
                        help='Regex in the name of scc->sa to be affected, '
                             'can be used multiple times')
    return parser.parse_args()


def match(matchers, vm_name):
    """Check whether the given vm name matches any of the regex match objects

    Args:
        matchers (list): A list of regex objects with match() method
        vm_name (string): The name of the VM to compare
    Returns:
        bool: whether or not the vm_name is matched by ANY of the regex in the list
    """
    for matcher in matchers:
        if matcher.match(vm_name):
            return True
    else:
        return False


def delete_stale_sa(provider, text_to_match):
    """ Checks global Security Context Constrains for stale Service Account records created during
        appliance deployment and removes such records if appliance doesn't exist any longer

    Args:
        provider: provider object
        text_to_match: (list) regexps which sa should match to

    Returns: None
    """
    logger.info("Checking scc in provider %s", provider.key)
    for scc_name in global_scc_names:
        scc = provider.mgmt.get_scc(scc_name)
        if not scc.users:
            logger.info("nothing to check. scc %s is empty", scc_name)
            continue
        for sa in scc.users:
            sa_namespace, sa_name = sa.split(':')[-2:]
            if match(text_to_match, sa_namespace) and not provider.mgmt.does_vm_exist(sa_namespace):
                logger.info('removing sa %s from scc %s', sa, scc_name)
                provider.mgmt.remove_sa_from_scc(scc_name=scc_name, namespace=sa_namespace,
                                                 sa=sa_name)
            else:
                logger.debug("skipping sa %s in scc %s because project exists "
                             "or it doesn't match any pattern", sa, scc_name)


if __name__ == "__main__":
    args = parse_cmd_line()
    errors = 0
    pf = ProviderFilter(classes=[OpenshiftProvider], required_fields=[('use_for_sprout', True)])
    with DummyAppliance():
        providers = list_providers(filters=[pf], use_global_filters=False)
    for prov in providers:
        # ping provider
        try:
            prov.mgmt.list_project()
        except Exception as e:
            logger.error('Connection to provider %s cannot be estabilished', prov.key)
            logger.error('Error: %s', e)
            errors += 1
            continue

        # remove all sa records from scc
        if args.cleanup_scc:
            try:
                text_to_match = [re.compile(r) for r in args.text_to_match]
                delete_stale_sa(prov, text_to_match)
            except Exception as e:
                logger.error('Error happened during security context cleanup')
                logger.error('Error: %s', e)
                errors += 1
                continue

    logger.info("Clean up process is over")
    sys.exit(errors)
