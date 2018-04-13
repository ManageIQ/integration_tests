#!/usr/bin/env python2

"""This script takes an provider and edomain as optional parameters, and
searches for old templates on specified provider's export domain and deletes
them. In case of no --provider parameter specified then this script
traverse all the rhevm providers in cfme_data.
"""

import argparse
import datetime
import pytz
from threading import Lock, Thread

from cfme.utils import conf, net
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

lock = Lock()

add_stdout_handler(logger)


def make_ssh_client(provider_mgmt):
    creds = conf.credentials[provider_mgmt.kwargs.get('ssh_creds')]

    connect_kwargs = {
        'username': creds['username'],
        'password': creds['password'],
        'hostname': provider_mgmt.kwargs.get('ipaddress')
    }
    return SSHClient(**connect_kwargs)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--edomain", dest="edomain",
                        help="Export domain for the remplate", default=None)
    parser.add_argument("--provider", dest="provider",
                        help="Rhevm provider (to look for in cfme_data)",
                        default=None)
    parser.add_argument("--days-old", dest="days_old",
                        help="number of days_old templates to be deleted"
                             "e.g. --day-old 4 deletes templates created before 4 days",
                        default=3)
    parser.add_argument("--max-templates", dest="max_templates",
                        help="max number of templates to be deleted at a time"
                             "e.g. --max-templates 6 deletes 6 templates at a time",
                        default=5)
    args = parser.parse_args()
    return args


def is_ovirt_engine_running(provider_mgmt):
    try:
        with make_ssh_client(provider_mgmt) as ssh_client:
            stdout = ssh_client.run_command('systemctl status ovirt-engine').output
            # fallback to sysV commands if necessary
            if 'command not found' in stdout:
                stdout = ssh_client.run_command('service ovirt-engine status').output
        return 'running' in stdout
    except Exception as e:
        logger.exception(e)
        return False


def change_edomain_state(provider_mgmt, state, edomain):
    try:
        # fetch name for logging
        provider_name = provider_mgmt.kwargs.get('name')
        log_args = (provider_name, edomain, state)

        api = provider_mgmt.api
        dcs = api.datacenters.list()
        for dc in dcs:
            export_domain = dc.storagedomains.get(edomain)
            if export_domain:
                if state == 'maintenance' and export_domain.get_status().state == 'active':
                    dc.storagedomains.get(edomain).deactivate()
                elif state == 'active' and export_domain.get_status().state != 'active':
                    dc.storagedomains.get(edomain).activate()

                wait_for(is_edomain_in_state, [api, state, edomain], fail_condition=False, delay=5)
                logger.info('RHEVM:%s, domain %s set to "%s" state', provider_name, edomain, state)
                return True
        return False
    except Exception:  # noqa
        logger.exception('RHEVM:%s Exception setting domain %s to "%s" state', *log_args)
        return False


def is_edomain_in_state(api, state, edomain):
    dcs = api.datacenters.list()
    for dc in dcs:
        export_domain = dc.storagedomains.get(edomain)
        if export_domain:
            return export_domain.get_status().state == state
    return False


# get the domain edomain path on the rhevm
def get_edomain_path(api, edomain):
    edomain_id = api.storagedomains.get(edomain).get_id()
    edomain_conn = api.storagedomains.get(edomain).storageconnections.list()[0]
    return ('{}/{}'.format(edomain_conn.get_path(), edomain_id),
            edomain_conn.get_address())


def cleanup_empty_dir_on_edomain(provider_mgmt, edomain):
    """Cleanup all the empty directories on the edomain/edomain_id/master/vms
    else api calls will result in 400 Error with ovf not found,
    Args:
        provider_mgmt: provider object under execution
        edomain: domain on which to operate
    """
    try:
        # We'll use this for logging
        provider_name = provider_mgmt.kwargs.get('name')
        # get path first
        path, edomain_ip = get_edomain_path(provider_mgmt.api, edomain)
        edomain_path = '{}:{}'.format(edomain_ip, path)

        tmp_dir = '~/tmp_filemount'
        commands = [
            'mkdir -p {}',
            'mount -O tcp {} {}'.format(edomain_path, tmp_dir),
            'find {}/master/vms/ -maxdepth 1 -type d -empty -delete'.format(tmp_dir),
            'cd ~ && umount {}'.format(tmp_dir),
            # split filename from tmp_dir
            'find . -maxdepth 1 -name {} -type d -empty -delete'.format(tmp_dir.split('/')[-1])
        ]

        logger.info('RHEVM:%s Deleting empty directories on edomain/vms file path %s',
                    provider_name, path)

        with make_ssh_client(provider_mgmt) as ssh_client:
            for cmd in commands:
                result = ssh_client.run_command(cmd)
                if result.failed:
                    # try to unmount
                    ssh_client.run_command('cd ~ && umout {}'.format(tmp_dir))
                    logger.info('RHEVM:%s Error running command %s while cleaning up: %s',
                          provider_name, cmd, result.output)

        logger.info('RHEVM:%s successfully deleted empty directories on path %s',
                    provider_name, path)
    except Exception as e:
        logger.exception(e)
        return False


def is_edomain_template_deleted(api, name, edomain):
    """Checks for the templates delete status on edomain.

    Args:
        api: API for RHEVM.
        name: template_name
        edomain: Export domain of selected RHEVM provider.
    """
    return not api.storagedomains.get(edomain).templates.get(name)


def delete_edomain_templates(api, template, edomain):
    """deletes the template on edomain.

    Args:
        api: API for RHEVM.
        name: template_name
        edomain: Export domain of selected RHEVM provider.
    """
    with lock:
        creation_time = template.get_creation_time().strftime("%d %B-%Y")
        name = template.get_name()
        logger.info('Deleting %s created on %s ...', name, creation_time)
    try:
        template.delete()
        logger.info('waiting for %s to be deleted..', name)
        wait_for(is_edomain_template_deleted, [api, name, edomain], fail_condition=False, delay=5)
        logger.info('RHEVM: successfully deleted template %s on domain %s', name, edomain)
    except Exception:
        with lock:
            logger.exception('RHEVM: Exception deleting template %s on domain %s', name, edomain)


def cleanup_templates(api, edomain, days, max_templates):
    try:
        templates = api.storagedomains.get(edomain).templates.list()
        thread_queue = []
        delete_templates = []
        for template in templates:
            delta = datetime.timedelta(days=days)
            now = datetime.datetime.now(pytz.utc)
            template_creation_time = template.get_creation_time().astimezone(pytz.utc)

            if template.get_name().startswith('auto-tmp'):
                if now > (template_creation_time + delta):
                    delete_templates.append(template)

        if not delete_templates:
            logger.info("RHEVM: No old templates to delete in %s", edomain)

        for delete_template in delete_templates[:max_templates]:
            thread = Thread(target=delete_edomain_templates,
                            args=(api, delete_template, edomain))
            thread.daemon = True
            thread_queue.append(thread)
            thread.start()

        for thread in thread_queue:
            thread.join()
    except Exception as e:
        logger.exception(e)
        return False


def api_params_resolution(item_list, item_name, item_param):
    """Picks and prints info about parameter obtained by api call.

    Args:
        item_list: List of possible candidates to pick from.
        item_name: Name of parameter obtained by api call.
        item_param: Name of parameter representing data in the script.
    """
    if len(item_list) == 0:
        logger.error("RHEVM: Cannot find %s (%s) automatically.", item_name, item_param)
        logger.error("Please specify it by cmd-line parameter '--%s' or in cfme_data.", item_param)
        return None
    elif len(item_list) > 1:
        logger.warning("RHEVM: Found multiple of %s. Picking first, '%s'.", item_name, item_list[0])
    else:
        logger.info("RHEVM: Found %s: '%s'.", item_name, item_list[0])

    return item_list[0]


def get_edomain(api):
    """Discovers suitable export domain automatically.

    Args:
        api: API to RHEVM instance.
    """
    edomain_names = []

    for domain in api.storagedomains.list(status=None):
        if domain.get_type() == 'export':
            edomain_names.append(domain.get_name())

    return api_params_resolution(edomain_names, 'export domain', 'edomain')


def make_kwargs(*args, **kwargs):
    """Assembles all the parameters in case of running as a standalone script.
       Makes sure, that the parameters given by command-line arguments
       have higher priority.Makes sure, that all the needed parameters
       have proper values.

    Args:
        args: Arguments given from command-line.
        kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm']
    """
    args_kwargs = dict(args._get_kwargs())

    if not kwargs:
        return args_kwargs

    template_name = kwargs.get('template_name')
    if template_name is None:
        template_name = conf.cfme_data['basic_info']['appliance_template']
        kwargs.update(template_name=template_name)

    for kkey, kval in kwargs.items():
        for akey, aval in args_kwargs.items():
            if aval and kkey == akey and kval != aval:
                kwargs[akey] = aval

    for akey, aval in args_kwargs.items():
        if akey not in kwargs.keys():
            kwargs[akey] = aval

    return kwargs


def run(**kwargs):
    """Calls the functions needed to cleanup templates on RHEVM providers.
       This is called either by template_upload_all script, or by main
       function.

    Args:
        **kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm'].
    """
    providers = conf.provider_data['management_systems']
    for provider in [prov for prov in providers if providers[prov]['type'] == 'rhevm']:

        # If a provider was passed, only cleanup on it, otherwise all rhevm providers
        cli_provider = kwargs.get('provider')
        if cli_provider and cli_provider != provider:
            continue

        logger.info("\n--------Start of %s--------", provider)
        provider_mgmt = get_mgmt(provider)

        try:
            # Raise exceptions here to log the end of provider section
            if not net.is_pingable(provider_mgmt.kwargs.get('ipaddress')):
                raise ValueError('Failed to ping provider.')
            elif not is_ovirt_engine_running(provider_mgmt):
                logger.error('ovirt-engine service not running..')
                raise ValueError('ovirt-engine not running on provider')

            logger.info('connecting to provider, to establish api handler')
            edomain = kwargs.get('edomain')
            if not edomain:
                edomain = provider_mgmt.kwargs['template_upload']['edomain']
            # Test API connection to provider, raises RequestError
            provider_mgmt.api  # noqa
        except Exception:
            logger.exception('Failed connecting to provider')
            logger.error("--------FAILURE End of %s--------\n", provider)
            continue

        try:
            cleanup_templates(provider_mgmt.api,
                              edomain,
                              kwargs.get('days_old'),
                              kwargs.get('max_templates'))
        finally:
            change_edomain_state(provider_mgmt,
                                 'maintenance',
                                 edomain)
            cleanup_empty_dir_on_edomain(provider_mgmt, edomain)

            change_edomain_state(provider_mgmt,
                                 'active',
                                 edomain)
            logger.info("--------End of %s--------\n", provider)

    logger.info("Provider Execution completed")


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = conf.cfme_data['template_upload']['template_upload_rhevm']

    final_kwargs = make_kwargs(*args, **kwargs)
    run(**final_kwargs)
