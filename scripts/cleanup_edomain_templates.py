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

from cfme.utils import net
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

lock = Lock()


def make_ssh_client(provider_mgmt):
    creds = credentials[provider_mgmt.kwargs.get('ssh_creds')]

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
            stdout = ssh_client.run_command('systemctl status ovirt-engine')[1]
            # fallback to sysV commands if necessary
            if 'command not found' in stdout:
                stdout = ssh_client.run_command('service ovirt-engine status')[1]
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
                print('RHEVM:{}, domain {} set to "{}" state'.format(*log_args))
                return True
        return False
    except Exception as e:
        print(e)
        print('RHEVM:{} Exception setting domain {} to "{}" state'.format(*log_args))
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

        command = 'mkdir -p ~/tmp_filemount &&'
        command += 'mount -O tcp {} ~/tmp_filemount &&'.format(edomain_path)
        command += 'find ~/tmp_filemount/master/vms/ -maxdepth 1 -type d -empty -delete &&'
        command += 'cd ~ && umount ~/tmp_filemount &&'
        command += 'find . -maxdepth 1 -name tmp_filemount -type d -empty -delete'

        print('RHEVM:{} Deleting empty directories on edomain/vms file path {}'
              .format(provider_name, path))

        with make_ssh_client(provider_mgmt) as ssh_client:
            exit_status, output = ssh_client.run_command(command)

        if exit_status != 0:
            print('RHEVM:{} Error deleting empty directories on path {}'
                  .format(provider_name, path))
            print(output)
        print('RHEVM:{} successfully deleted empty directories on path {}'
              .format(provider_name, path))
    except Exception as e:
        print(e)
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
        print('Deleting {} created on {} ...'.format(name, creation_time))
    try:
        template.delete()
        print('waiting for {} to be deleted..'.format(name))
        wait_for(is_edomain_template_deleted, [api, name, edomain], fail_condition=False, delay=5)
        print('RHEVM: successfully deleted template {} on domain {}'.format(name, edomain))
    except Exception as e:
        with lock:
            print('RHEVM: Exception deleting template {} on domain {}'.format(name, edomain))
            logger.exception(e)


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
            print("RHEVM: No old templates to delete in {}".format(edomain))

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
        print("RHEVM: Cannot find {} ({}) automatically.".format(item_name, item_param))
        print("Please specify it by cmd-line parameter '--{}' or in cfme_data.".format(item_param))
        return None
    elif len(item_list) > 1:
        print("RHEVM: Found multiple of {}. Picking first, '{}'.".format(item_name, item_list[0]))
    else:
        print("RHEVM: Found {}: '{}'.".format(item_name, item_list[0]))

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


def make_kwargs(args, cfme_data, **kwargs):
    """Assembles all the parameters in case of running as a standalone script.
       Makes sure, that the parameters given by command-line arguments
       have higher priority.Makes sure, that all the needed parameters
       have proper values.

    Args:
        args: Arguments given from command-line.
        cfme_data: Data in cfme_data.yaml
        kwargs: Kwargs generated from
        cfme_data['template_upload']['template_upload_rhevm']
    """
    args_kwargs = dict(args._get_kwargs())

    if not kwargs:
        return args_kwargs

    template_name = kwargs.get('template_name')
    if template_name is None:
        template_name = cfme_data['basic_info']['appliance_template']
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
    providers = cfme_data['management_systems']
    for provider in [prov for prov in providers if providers[prov]['type'] == 'rhevm']:

        # If a provider was passed, only cleanup on it, otherwise all rhevm providers
        cli_provider = kwargs.get('provider')
        if cli_provider and cli_provider != provider:
            continue

        provider_mgmt = get_mgmt(provider)

        if not net.is_pingable(provider_mgmt.kwargs.get('ipaddress')):
            continue
        elif not is_ovirt_engine_running(provider_mgmt):
            print('ovirt-engine service not running..')
            continue

        try:
            print('connecting to provider, to establish api handler')
            edomain = kwargs.get('edomain')
            if not edomain:
                edomain = provider_mgmt.kwargs['template_upload']['edomain']
        except Exception as e:
            logger.exception(e)
            continue

        try:
            print("\n--------Start of {}--------".format(provider))
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
            print("--------End of {}--------\n".format(provider))

    print("Provider Execution completed")


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_rhevm']

    final_kwargs = make_kwargs(args, cfme_data, **kwargs)
    run(**final_kwargs)
