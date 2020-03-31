#!/usr/bin/env python3
"""This script takes a provider and edomain as optional parameters, and
searches for old templates on specified provider's export domain and deletes
them. In case of no --provider parameter specified then this script
runs against all the rhevm providers in cfme_data.
"""
import argparse
import datetime
import sys
from multiprocessing.pool import ThreadPool

import pytz

from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient

add_stdout_handler(logger)  # log to stdout


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--export-domain",
                        dest="domain",
                        default=None,
                        help="Export domain for the template")
    parser.add_argument("--provider",
                        dest="provider",
                        default=None,
                        help="RHV provider (to look for in cfme_data)")
    parser.add_argument("--days-old",
                        dest="days_old",
                        default=3,
                        help="number of days_old templates to be deleted"
                             "e.g. --day-old 4 deletes templates created before 4 days")
    parser.add_argument("--max-templates",
                        dest="max_templates",
                        default=5,
                        help="max number of templates to be deleted at a time"
                             "e.g. --max-templates 6 deletes 6 templates at a time")
    args = parser.parse_args()
    return args


# get the domain domain path on the RHV
def get_domain_path(provider_mgmt, domain):
    domain = provider_mgmt.api.system_service().storage_domains_service().list(
        search=f'name={domain}',
        follow='storage_connections')[0]
    domain_conn = domain.storage_connections[0]
    return domain_conn.path, domain.id, domain_conn.address


def cleanup_empty_dir_on_domain(provider_mgmt, domain):
    """Cleanup all the empty directories on the domain/domain_id/master/vms
    else api calls will result in 400 Error with ovf not found,

    Args:
        provider_mgmt: provider object under execution
        domain: domain on which to operate

    Returns:
        bool - False if exception or command failure, True if successful cleanup command

    """
    try:
        # We'll use this for logging
        provider_key = provider_mgmt.kwargs.get('provider_key')
        # get path first
        path, id, addr = get_domain_path(provider_mgmt, domain)
        domain_path = f'{addr}:{path}/{id}'

        command = ['mkdir -p ~/tmp_filemount &&',
                   f'mount -O tcp {domain_path} ~/tmp_filemount &&',
                   'find ~/tmp_filemount/master/vms/ -maxdepth 1 -type d -empty -delete &&',
                   'cd ~ && umount ~/tmp_filemount &&',
                   'find . -maxdepth 1 -name tmp_filemount -type d -empty -delete']

        logger.info('%s Deleting empty directories on domain/vms file path %s',
                    provider_key, path)

        creds = credentials[provider_mgmt.kwargs.get('ssh_creds')]

        connect_kwargs = {
            'username': creds['username'],
            'password': creds['password'],
            'hostname': provider_mgmt.kwargs.get('ipaddress')
        }
        with SSHClient(**connect_kwargs) as ssh_client:
            result = ssh_client.run_command(' '.join(command))

        if result.failed:
            logger.info('%s: Error deleting empty directories on path %s, with output: %s',
                        provider_key, path, result.output)
            return False

        logger.info('%s: successfully deleted empty directories on path %s', provider_key, path)
        return True
    except Exception:
        logger.exception('%s: Exception trying to cleanup empty dir', provider_key)
        return False


def delete_domain_template(provider_mgmt, template, domain):
    """deletes the template on domain.

    Args:
        provider_mgmt: API for RHV.
        name: template_name
        domain: Export domain of selected RHV provider.
    """
    try:
        template.delete()
        logger.info('%s: successfully deleted template %s on domain %s',
                    provider_mgmt.kwargs.get('provider_key'),
                    template.name,
                    domain)
    except Exception:
        logger.exception('%s: Exception deleting template %s on domain %s', template.name, domain)


def cleanup_templates(provider_mgmt, domain, days, max_templates):
    try:
        templates = provider_mgmt.list_templates_from_storage_domain(domain)
        delete_templates = []
        targeted_templates = [t for t in templates
                              if t.name.startswith('auto-tmp') or t.name.startswith('raw-')]
        for template in targeted_templates:
            if datetime.datetime.now(pytz.utc) > (template.creation_time.astimezone(pytz.utc) +
                                                  datetime.timedelta(days=days)):
                logger.info('Marking for delete: %s created on %s',
                            template.name,
                            template.creation_time.strftime("%d %B-%Y"))
                delete_templates.append(template)

        if not delete_templates:
            logger.info("%s: No old templates to delete in %s",
                        provider_mgmt.kwargs.get('provider_key', '<key attr not found>'),
                        domain)
            return False

        with ThreadPool(max_templates) as pool:
            pool.starmap(
                delete_domain_template,
                ((provider_mgmt, delete_template, domain) for delete_template in delete_templates)
            )

    except Exception:
        logger.exception('Unexpected exception trying to cleanup templates on %s',
                         provider_mgmt.kwargs.get('provider_key', '<key attr not found>'))
        return False

    return True


def run(domain, provider_key, days_old, max_templates):
    """Calls the functions needed to cleanup templates on RHV providers.
       This is called either by template_upload_all script, or by main
       function.

    Args:
        domain: see argparse
        provider_key: see argparse
        days_old: see argparse
        max_templates: see argparse
    """
    providers = cfme_data['management_systems']
    for provider in [prov for prov in providers if providers[prov]['type'] == 'rhevm']:

        # If a provider was passed, only cleanup on it, otherwise all RHV providers
        if provider_key and provider_key != provider:
            logger.info('Skipping provider [%s], does not match passed key', provider)
            continue

        domain_to_clean = (domain or
                           providers[provider].get('template_upload', {}).get('edomain'))
        if domain_to_clean is None:
            logger.info('Skipping provider [%s], no domain under template_upload', provider)
            continue

        logger.info("\n--------Start of %s--------", provider)
        provider_mgmt = get_mgmt(provider)

        try:
            # Test API connection to provider, raises RequestError
            prov_test = provider_mgmt.api.test()  # noqa
        except Exception:
            prov_test = False

        if prov_test is False:
            logger.exception('Failed connecting to provider')
            logger.info("-------- FAILURE End of %s --------\n", provider)
            continue

        cleanup = False
        try:
            cleanup = cleanup_templates(provider_mgmt, domain_to_clean, days_old, max_templates)
        finally:
            if cleanup:
                logger.info('Changing domain to maintenance mode: %s', domain_to_clean)
                provider_mgmt.change_storage_domain_state('maintenance', domain_to_clean)

                cleanup_empty_dir_on_domain(provider_mgmt, domain_to_clean)

                logger.info('Changing domain to active mode: %s', domain_to_clean)
                provider_mgmt.change_storage_domain_state('active', domain_to_clean)
            logger.info("-------- End of %s --------\n", provider)

    logger.info("Provider cleanup completed")


if __name__ == "__main__":
    args = parse_cmd_line()

    sys.exit(run(args.domain, args.provider, args.days_old, args.max_templates))
