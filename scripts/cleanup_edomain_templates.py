#!/usr/bin/env python2

"""This script takes an provider and edomain as optional parameters, and
searches for old templates on specified provider's export domain and deletes
them. In case of no --provider parameter specified then this script
traverse all the rhevm providers in cfme_data.
"""

import argparse
import datetime
import pytz
import sys
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


def is_ovirt_engine_running(rhevm_ip, sshname, sshpass):
    try:
        ssh_client = make_ssh_client(rhevm_ip, sshname, sshpass)
        stdout = ssh_client.run_command('service ovirt-engine status')[1]
        ssh_client.close()
        if 'running' not in stdout:
            return False
        return True
    except Exception as e:
        logger.exception(e)
        return False


class CleanupRhevm(object):

    def __init__(self, api):
        self.api = api

    def is_edomain_in_state(self, state, edomain):
        dcs = self.api.datacenters.list()
        for dc in dcs:
            export_domain = dc.storagedomains.get(edomain)
            if export_domain:
                return export_domain.get_status().state == state
        return False

    def change_edomain_state(self, provider, state, edomain):
        try:
            dcs = self.api.datacenters.list()
            for dc in dcs:
                export_domain = dc.storagedomains.get(edomain)
                if export_domain:
                    if state == 'maintenance' and export_domain.get_status().state == 'active':
                        dc.storagedomains.get(edomain).deactivate()
                    elif state == 'active' and export_domain.get_status().state != 'active':
                        dc.storagedomains.get(edomain).activate()

                    wait_for(self.is_edomain_in_state,
                             [state, edomain], fail_condition=False, delay=5)
                    print('RHEVM:{} {} successfully set to {} state'.format(provider,
                                                                            edomain, state))
                    return True
            return False
        except Exception as e:
            logger.exception(e)
            print("RHEVM:{} Exception occurred while changing {} state to {}".format(
                provider, edomain, state))
            return False

    # get the domain edomain path on the rhevm
    def get_edomain_path(self, edomain):
        edomain_id = self.api.storagedomains.get(edomain).get_id()
        edomain_conn = self.api.storagedomains.get(edomain).storageconnections.list()[0]
        return (edomain_conn.get_path() + '/' + edomain_id,
                edomain_conn.get_address())

    def cleanup_empty_dir_on_edomain(self, path, provider, edomainip,
                                     provider_ip, sshname, sshpass):
        """Cleanup all the empty directories on the edomain/edomain_id/master/vms
        else api calls will result in 400 Error with ovf not found,

        Args:
            path: path for vms directory on edomain.
            edomain: Export domain of chosen RHEVM provider.
            edomainip: edomainip to connect through ssh.
            sshname: edomain ssh credentials.
            sshpass: edomain ssh credentials.
            provider: provider under execution
            provider_ip: provider ip address
        """
        try:
            ssh_client = make_ssh_client(provider_ip, sshname, sshpass)
            edomain_path = edomainip + ':' + path
            command = 'mkdir ~/tmp_filemount && mount -O tcp {} ~/tmp_filemount &&'.format(
                edomain_path)
            command += 'cd ~/tmp_filemount/master/vms &&'
            command += 'find . -maxdepth 1 -type d -empty -delete &&'
            command += 'cd ~ && umount ~/tmp_filemount &&'
            command += 'find . -maxdepth 1 -name tmp_filemount -type d -empty -delete'
            print("RHEVM:{} Deleting the empty directories on edomain/vms file...".format(provider))
            exit_status, output = ssh_client.run_command(command)
            ssh_client.close()
            if exit_status != 0:
                print("RHEVM:{} Error while deleting the empty directories on path..".format(
                    provider))
                print(output)
        except Exception as e:
            logger.exception(e)
            return False

    def is_edomain_template_deleted(self, name, edomain):
        """Checks for the templates delete status on edomain.

        Args:
            api: API for RHEVM.
            name: template_name
            edomain: Export domain of selected RHEVM provider.
        """
        return not self.api.storagedomains.get(edomain).templates.get(name)

    def delete_edomain_templates(self, provider, template, edomain):
        """deletes the template on edomain.

        Args:
            api: API for RHEVM.
            name: template_name
            edomain: Export domain of selected RHEVM provider.
        """
        with lock:
            creation_time = template.get_creation_time().strftime("%d %B-%Y")
            name = template.get_name()
            print('RHEVM:{} Deleting {} created on {} ...'.format(provider, name, creation_time))
        try:
            template.delete()
            print('RHEVM:{} waiting for {} to be deleted..'.format(provider, name))
            wait_for(self.is_edomain_template_deleted,
                     [name, edomain], fail_condition=False, delay=5)
            print("RHEVM:{} successfully deleted the template {}".format(provider, name))
        except Exception as e:
            with lock:
                print("RHEVM:{} Exception occurred while deleting the template {}".format(
                    provider, name))
                logger.exception(e)

    def cleanup_templates(self, provider, edomain, days, max_templates):
        try:
            templates = self.api.storagedomains.get(edomain).templates.list()
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
                print("RHEVM:{} No old templates to delete in {}".format(provider, edomain))

            for delete_template in delete_templates[:max_templates]:
                thread = Thread(target=self.delete_edomain_templates,
                                args=(provider, delete_template, edomain))
                thread.daemon = True
                thread_queue.append(thread)
                thread.start()

            for thread in thread_queue:
                thread.join()
        except Exception as e:
            logger.exception(e)
            return False

    # sometimes, rhevm is just not cooperative. This is function used to wait for template on
    # export domain to become unlocked
    def check_edomain_template(self, edomain, temp_tmp_name):
        '''
        checks for the edomain templates status, and returns True, if template state is ok
        otherwise returns False. try, except block returns the False in case of Exception,
        as wait_for handles the timeout Exceptions.
        :param api: API to chosen RHEVM provider.
        :param edomain: export domain.
        :return: True or False based on the template status.
        '''
        try:
            template = self.api.storagedomains.get(edomain).templates.get(temp_tmp_name)
            if template.get_status().state != "ok":
                return False
            return True
        except Exception:
            return False

    def cleanuptmp(self, edomain, ssh_client, ovaname, provider,
                   temp_tmp_name, temp_vm_name):
        """Cleans up all the mess that the previous functions left behind.

        Args:
            api: API to chosen RHEVM provider.
            edomain: Export domain of chosen RHEVM provider.
        """
        try:
            print("RHEVM:{} Deleting the  .ova file...".format(provider))
            command = 'rm {}'.format(ovaname)
            exit_status, output = ssh_client.run_command(command)

            print("RHEVM:{} Deleting the temp_vm on sdomain...".format(provider))
            temporary_vm = self.api.vms.get(temp_vm_name)
            if temporary_vm:
                temporary_vm.delete()

            print("RHEVM:{} Deleting the temp_template on sdomain...".format(provider))
            temporary_template = self.api.templates.get(temp_tmp_name)
            if temporary_template:
                temporary_template.delete()

            # waiting for template on export domain
            unimported_template = self.api.storagedomains.get(edomain).templates.get(
                temp_tmp_name)
            print("RHEVM:{} waiting for template on export domain...".format(provider))
            wait_for(self.check_edomain_template, [edomain, temp_tmp_name],
                     fail_condition=False, delay=5)

            if unimported_template:
                print("RHEVM:{} deleting the template on export domain...".format(provider))
                unimported_template.delete()

            print("RHEVM:{} waiting for template delete on export domain...".format(provider))
            wait_for(self.is_edomain_template_deleted, [temp_tmp_name, edomain],
                     fail_condition=False, delay=5)

        except Exception as e:
            logger.exception(e)
            print("RHEVM:{} Exception occurred in cleanup method".format(provider))
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

        mgmt_sys = cfme_data['management_systems'][provider]
        ssh_rhevm_creds = mgmt_sys['hosts'][0]['credentials']
        sshname = credentials[ssh_rhevm_creds]['username']
        sshpass = credentials[ssh_rhevm_creds]['password']
        provider_ip = cfme_data['management_systems'][provider]['ipaddress']

        if not net.is_pingable(provider_ip):
            continue
        elif not is_ovirt_engine_running(provider_ip, sshname, sshpass):
            print('RHEVM:{} ovirt-engine service not running..'.format(provider))
            continue

        try:
            print('RHEVM:{} connecting to provider, to establish api handler'.format(provider))
            api = get_mgmt(provider).api

            cleanuprhevm = CleanupRhevm(api)

            edomain = get_edomain(api)
            if args.edomain:
                edomain = args.edomain
            path, edomain_ip = cleanuprhevm.get_edomain_path(edomain)
        except Exception as e:
            logger.exception(e)
            continue

        try:
            print("\n--------Start of {}--------".format(provider))
            cleanuprhevm.cleanup_templates(provider, edomain, args.days_old, args.max_templates)
        finally:
            cleanuprhevm.change_edomain_state(provider, 'maintenance', edomain)
            cleanuprhevm.cleanup_empty_dir_on_edomain(path, provider, edomain_ip,
                                                      provider_ip, sshname, sshpass)
            cleanuprhevm.change_edomain_state(provider, 'active', edomain)
            print("--------End of {}--------\n".format(provider))
    print("Provider Execution completed")
    sys.exit(0)

if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_rhevm']

    final_kwargs = make_kwargs(args, cfme_data, **kwargs)
    sys.exit(run(**final_kwargs))
