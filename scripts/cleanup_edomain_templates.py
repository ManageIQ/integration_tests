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

from utils import net
from utils.conf import cfme_data
from utils.conf import credentials
from utils.ssh import SSHClient
from utils.log import logger
from utils.providers import get_mgmt
from utils.wait import wait_for

lock = Lock()


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


def make_ssh_client(rhevip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': rhevip
    }
    return SSHClient(**connect_kwargs)


def change_edomain_state(api, state, edomain):
    try:
        dcs = api.datacenters.list()
        for dc in dcs:
            export_domain = dc.storagedomains.get(edomain)
            if export_domain:
                if state == 'maintenance' and export_domain.get_status().state == 'active':
                    dc.storagedomains.get(edomain).deactivate()
                elif state == 'active' and export_domain.get_status().state != 'active':
                    dc.storagedomains.get(edomain).activate()

                wait_for(is_edomain_template_deleted,
                         [api, state, edomain], fail_condition=False, delay=5)
                print('{} successfully set to {} state'.format(edomain, state))
                return True
        return False
    except Exception:
        print("Exception occurred while changing {} state to {}".format(edomain, state))
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
    return (edomain_conn.get_path() + '/' + edomain_id,
            edomain_conn.get_address())


def cleanup_empty_dir_on_edomain(path, edomainip, sshname, sshpass):
    """Cleanup all the empty directories on the edomain/edomain_id/master/vms
    else api calls will result in 400 Error with ovf not found,

    Args:
        path: path for vms directory on edomain.
        edomain: Export domain of chosen RHEVM provider.
        edomainip: edomainip to connect through ssh.
        sshname: edomain ssh credentials.
        sshpass: edomain ssh credentials.
    """
    print("RHEVM: Deleting the empty directories on edomain/vms file...")
    ssh_client = make_ssh_client(edomainip, sshname, sshpass)
    command = 'cd {}/master/vms && find . -maxdepth 1 -type d -empty -delete'.format(path)
    exit_status, output = ssh_client.run_command(command)
    if exit_status != 0:
        print("RHEVM: Error while deleting the empty directories on path..")
        print(output)


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
        wait_for(is_edomain_template_deleted,
                 [api, name, edomain], fail_condition=False, delay=5)
        print("RHEVM: successfully deleted the template {}".format(name))
    except Exception as e:
        with lock:
            print("RHEVM: Exception occurred while deleting the template {}".format(name))
            logger.exception(e)


def cleanup_templates(api, edomain, days, max_templates):
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
        print("RHEVM: Found multiple instances of {}. Picking '{}'.".format(
            item_name, item_list[0]))
    else:
        print("RHEVM: Found {} '{}'.".format(item_name, item_list[0]))

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

    template_name = kwargs.get('template_name', None)
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
        **kwargs: Kwargs generated from
        cfme_data['template_upload']['template_upload_rhevm'].
    """
    providers = cfme_data['management_systems']
    for provider in providers:
        if cfme_data['management_systems'][provider]['type'] != 'rhevm':
            continue
        if args.provider:
            if args.provider != provider:
                continue
        if not net.is_pingable(cfme_data['management_systems'][provider]['ipaddress']):
            continue
        mgmt_sys = cfme_data['management_systems'][provider]
        ssh_rhevm_creds = mgmt_sys['hosts'][0]['credentials']
        sshname = credentials[ssh_rhevm_creds]['username']
        sshpass = credentials[ssh_rhevm_creds]['password']

        try:
            api = get_mgmt(provider).api
            edomain = get_edomain(api)
            if args.edomain:
                edomain = args.edomain
            path, edomain_ip = get_edomain_path(api, edomain)
        except Exception:
            continue

        try:
            print("\n--------Start of {}--------".format(provider))
            cleanup_templates(api, edomain, args.days_old, args.max_templates)
        finally:
            change_edomain_state(api, 'maintenance', edomain)
            cleanup_empty_dir_on_edomain(path, edomain_ip, sshname, sshpass)
            change_edomain_state(api, 'active', edomain)
            print("--------End of {}--------\n".format(provider))


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_rhevm']

    final_kwargs = make_kwargs(args, cfme_data, **kwargs)
    run(**final_kwargs)
