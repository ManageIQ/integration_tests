#!/usr/bin/env python3
"""Clone a template on a given provider to a VM instance

Where possible, defaults will come from cfme_data"""
import argparse
import sys

import yaml
from wrapanapi import Openshift
from wrapanapi import VmState

from cfme.utils.appliance import Appliance
from cfme.utils.appliance import IPAppliance
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials as cred
from cfme.utils.conf import provider_data
from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.net import find_pingable
from cfme.utils.path import log_path
from cfme.utils.providers import get_mgmt
from cfme.utils.trackerbot import api
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

# log to stdout
add_stdout_handler(logger)


def parse_cmd_line():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    # required options (heh)
    parser.add_argument('--provider', help='provider key in cfme_data')
    parser.add_argument('--template', help='the name of the template to clone')
    parser.add_argument('--vm_name', help='the name of the VM to create')

    # generic options
    parser.add_argument('--deploy', dest='deploy',
                        help='deploy True/False, this option to be used only to deploy template'
                             'this option force the script to use local provider_data,'
                             'and not cfme_data on non-cfmeqe providers from jenkins job',
                        default=None)
    parser.add_argument('--destroy', dest='destroy', action='store_true',
                        help='Destroy the destination VM')
    parser.add_argument('--configure', default=False, action='store_true',
                        help='configure the VM after provisioning')
    parser.add_argument('--no-cleanup', default=True, action='store_false',
                        dest='cleanup', help="don't clean up the vm on clone failure")
    parser.add_argument('--log', dest='loglevel', default='WARNING',
                        help='Set the log level')
    parser.add_argument('--outfile', dest='outfile',
                        help='Write provisioning details to the named file', default='')

    # sub options organized for provider types
    rhev_parser = parser.add_argument_group('rhev')
    rhev_parser.add_argument('--cluster', default=None,
                             help='the name of the VM on which to act')
    rhev_parser.add_argument('--place_policy_host', default=None,
                             help='the host for the vm to start on')
    rhev_parser.add_argument('--place_policy_aff', default=None,
                             help='the affinity of the vm on a host')

    cloud_parser = parser.add_argument_group('cloud')
    cloud_parser.add_argument('--flavor', default=None, help='ec2/rhos flavor')

    openstack_parser = parser.add_argument_group('openstack')
    openstack_parser.add_argument('--floating-ip-pool', default=None,
                                  help='openstack floating ip pool to use')

    args = parser.parse_args()
    return args


def destroy_vm(provider_mgmt, vm_name):
    """Given a provider backend and VM name, destroy an instance with logging and error guards

    Returns ``True`` if the VM is deleted, ``False`` if the backend reports that it did not delete
        the VM, and ``None`` if an error occurred (the error will be logged)

    """
    try:
        if provider_mgmt.does_vm_exist(vm_name):
            logger.info('Destroying VM %s', vm_name)

            # TODO: change after openshift wrapanapi refactor
            if isinstance(provider_mgmt, Openshift):
                vm_deleted = provider_mgmt.delete_vm(vm_name)
            else:
                vm = provider_mgmt.get_vm(vm_name)
                vm_deleted = vm.cleanup()
            if vm_deleted:
                logger.info('VM %s destroyed', vm_name)
            else:
                logger.error('Destroying VM %s failed for unknown reasons', vm_name)
            return vm_deleted
    except Exception as e:
        logger.error('%s destroying VM %s (%s)', type(e).__name__, vm_name, str(e))


def cloud_init_done(appliance):
    """
    Make sure cloud-init scripts have completed
    """
    logger.info("Checking if ssh login works and cloud-init is done...")
    appliance.wait_for_ssh()
    success = appliance.ssh_client.run_command('cat /var/lib/cloud/instance/boot-finished').success
    if success:
        logger.info("cloud-init done!")
    return success


def attach_gce_disk(vm):
    """
    Attach a 5gb persistent disk for DB storage on GCE instance

    Disk is marked for auto-delete by wrapanapi
    """
    logger.info("Attaching a DB disk to GCE instance")
    vm.stop()
    disk_name = "{}-db-disk".format(vm.name)
    vm.system.create_disk(disk_name, size_gb=5)
    vm.attach_disk(disk_name)
    vm.start()


def main(**kwargs):
    # get_mgmt validates, since it will explode without an existing key or type
    if kwargs.get('deploy'):
        kwargs['configure'] = True
        kwargs['outfile'] = 'appliance_ip_address_1'
        providers = provider_data['management_systems']
        provider_dict = provider_data['management_systems'][kwargs['provider']]
        credentials =\
            {'username': provider_dict['username'],
             'password': provider_dict['password'],
             'tenant': provider_dict['template_upload'].get('tenant_admin', 'admin'),
             'auth_url': provider_dict.get('auth_url'),
             }
        provider = get_mgmt(kwargs['provider'], providers=providers, credentials=credentials)
        provider_type = provider_data['management_systems'][kwargs['provider']]['type']
        deploy_args = {
            'vm_name': kwargs['vm_name'],
            'template': kwargs['template'],
        }
    else:
        provider = get_mgmt(kwargs['provider'])
        provider_dict = cfme_data['management_systems'][kwargs['provider']]
        provider_type = provider_dict['type']
        deploy_args = {
            'vm_name': kwargs['vm_name'],
            'template': kwargs['template'],
        }

    yaml_flavor = [
        provider_dict.get('sprout', {}).get('flavor_name')
        or provider_dict.get('provisioning', {}).get('instance_type')
        or provider_dict.get('template_upload', {}).get('flavor_name')
    ]  # None if none of them are set

    logger.info('Connecting to %s', kwargs['provider'])

    if kwargs.get('destroy'):
        # TODO: destroy should be its own script
        # but it's easy enough to just hijack the parser here
        # This returns True if destroy fails to give POSIXy exit codes (0 is good, False is 0, etc)
        return not destroy_vm(provider, deploy_args['vm_name'])

    # Try to snag defaults from cfme_data here for each provider type
    if provider_type == 'rhevm':
        cluster = provider_dict.get('default_cluster', kwargs.get('cluster'))
        if cluster is None:
            raise Exception('--cluster is required for rhev instances and default is not set')
        deploy_args['cluster'] = cluster

        if kwargs.get('place_policy_host') and kwargs.get('place_policy_aff'):
            deploy_args['placement_policy_host'] = kwargs['place_policy_host']
            deploy_args['placement_policy_affinity'] = kwargs['place_policy_aff']
    elif provider_type == 'ec2':
        # ec2 doesn't have an api to list available flavors, so the first flavor is the default
        try:
            # c3.xlarge has 4 CPU cores and 7.5GB RAM - minimal requirements for CFME Appliance
            flavor = kwargs.get('flavor', 'c3.xlarge')
        except IndexError:
            raise Exception('--flavor is required for EC2 instances and default is not set')
        deploy_args['instance_type'] = flavor
        deploy_args['key_name'] = "shared"
        # we want to override default cloud-init which disables root login and password login
        cloud_init_dict = {
            'chpasswd':
            {
                'expire': False,
                'list': '{}:{}\n'.format(cred['ssh']['username'], cred['ssh']['password'])
            },
            'disable_root': False,
            'ssh_pwauth': True
        }
        cloud_init = "#cloud-config\n{}".format(yaml.safe_dump(cloud_init_dict,
                                                               default_flow_style=False))
        deploy_args['user_data'] = cloud_init
    elif provider_type == 'openstack':
        # filter openstack flavors based on what's available
        available_flavors = provider.list_flavor()
        logger.info("Available flavors on provider: %s", available_flavors)
        generic_flavors = [f for f in yaml_flavor if f in available_flavors]

        try:
            # TODO py3 filter needs next() instead of indexing
            flavor = (kwargs.get('flavor', yaml_flavor) or generic_flavors[0])
        except IndexError:
            raise Exception('flavor is required for RHOS instances and '
                            'default is not set or unavailable on provider')
        logger.info('Selected flavor: %s', flavor)

        deploy_args['flavor_name'] = flavor

        network_name = (kwargs.get('network_name') or
                        provider_dict.get('sprout', {}).get('network_name'))

        logger.info('Selected Network: %s', network_name)

        if network_name is not None:
            deploy_args['network_name'] = network_name

        provider_pools = [p.name for p in provider.api.floating_ip_pools.list()]
        try:
            # TODO: If there are multiple pools, have a provider default in cfme_data
            floating_ip_pool = kwargs.get('floating_ip_pool') or provider_pools[0]
        except IndexError:
            raise Exception('No floating IP pools available on provider')

        if floating_ip_pool is not None:
            logger.info('Selected floating ip pool: %s', floating_ip_pool)
            deploy_args['floating_ip_pool'] = floating_ip_pool
    elif provider_type == "virtualcenter":
        if "allowed_datastores" in provider_dict:
            deploy_args["allowed_datastores"] = provider_dict["allowed_datastores"]
    elif provider_type == 'scvmm':
        deploy_args["host_group"] = provider_dict["provisioning"]['host_group']
    elif provider_type == 'gce':
        deploy_args['ssh_key'] = '{user_name}:{public_key}'.format(
            user_name=cred['ssh']['ssh-user'],
            public_key=cred['ssh']['public_key'])
    elif provider_type == 'openshift':
        trackerbot = api()
        raw_tags = trackerbot.providertemplate().get(provider=kwargs['provider'],
                                                     template=deploy_args['template'])['objects']
        raw_tags = raw_tags[-1]['template'].get('custom_data', "{}")
        deploy_args["tags"] = yaml.safe_load(raw_tags)['TAGS']
    # Do it!
    try:
        logger.info(
            'Cloning %s to %s on %s',
            deploy_args['template'], deploy_args['vm_name'], kwargs['provider']
        )
        # TODO: change after openshift wrapanapi refactor
        output = None  # 'output' is only used for openshift providers
        if isinstance(provider, Openshift):
            output = provider.deploy_template(**deploy_args)
        else:
            template = provider.get_template(deploy_args['template'])
            template.deploy(**deploy_args)

    except Exception as e:
        logger.exception(e)
        logger.error('template deploy failed')
        if kwargs.get('cleanup'):
            logger.info('attempting to destroy %s', deploy_args['vm_name'])
            destroy_vm(provider, deploy_args['vm_name'])
        return 12

    if not provider.does_vm_exist(deploy_args['vm_name']):
        logger.error('provider.deploy_template failed without exception')
        return 12

    # TODO: change after openshift wrapanapi refactor
    if isinstance(provider, Openshift):
        if provider.is_vm_running(deploy_args['vm_name']):
            logger.info('VM %s is running', deploy_args['vm_name'])
        else:
            logger.error('VM %s is not running', deploy_args['vm_name'])
            return 10
    else:
        vm_mgmt = provider.get_vm(deploy_args['vm_name'])
        vm_mgmt.ensure_state(VmState.RUNNING, timeout='5m')
        if provider_type == 'gce':
            try:
                attach_gce_disk(vm_mgmt)
            except Exception:
                logger.exception("Failed to attach db disk")
                destroy_vm(provider, deploy_args['vm_name'])
                return 10

    if provider_type == 'openshift':
        vm_ip = output['url']
    else:
        try:
            vm_ip, _ = wait_for(
                find_pingable,
                func_args=[vm_mgmt],
                fail_condition=None,
                delay=5,
                num_sec=300
            )
        except TimedOutError:
            msg = 'Timed out waiting for reachable depot VM IP'
            logger.exception(msg)
            return 10

    try:
        if kwargs.get('configure'):
            logger.info('Configuring appliance, this can take a while.')
            if kwargs.get('deploy'):
                app = IPAppliance(hostname=vm_ip)
            else:
                app_args = (kwargs['provider'], deploy_args['vm_name'])
                app_kwargs = {}
                if provider_type == 'openshift':
                    ocp_creds = cred[provider_dict['credentials']]
                    ssh_creds = cred[provider_dict['ssh_creds']]
                    app_kwargs = {
                        'project': output['project'],
                        'db_host': output['external_ip'],
                        'container': 'cloudforms-0',
                        'hostname': vm_ip,
                        'openshift_creds': {
                            'hostname': provider_dict['hostname'],
                            'username': ocp_creds['username'],
                            'password': ocp_creds['password'],
                            'ssh': {
                                'username': ssh_creds['username'],
                                'password': ssh_creds['password'],
                            },
                        }
                    }
                app = Appliance.from_provider(*app_args, **app_kwargs)

            if provider_type == 'ec2':
                wait_for(
                    cloud_init_done, func_args=[app], num_sec=600, handle_exception=True, delay=5)
            if provider_type == 'gce':
                app.configure_gce()
            elif provider_type == 'openshift':
                # openshift appliances don't need any additional configuration
                pass
            else:
                app.configure()
            logger.info('Successfully Configured the appliance.')
    except Exception as e:
        logger.exception(e)
        logger.error('Appliance Configuration Failed')
        if not kwargs.get('deploy'):
            app = Appliance.from_provider(kwargs['provider'], deploy_args['vm_name'])
            ssh_client = app.ssh_client()
            result = ssh_client.run_command('find /root/anaconda-post.log')
            if result.success:
                ssh_client.get_file('/root/anaconda-post.log',
                                    log_path.join('anaconda-post.log').strpath)
            ssh_client.close()
        destroy_vm(app.provider, deploy_args['vm_name'])
        return 10

    if kwargs.get('outfile') or kwargs.get('deploy'):
        # todo: to get rid of those scripts in jenkins or develop them from scratch
        with open(kwargs['outfile'], 'w') as outfile:
            if provider_type == 'openshift':
                output_data = {
                    'appliances':
                        [
                            {
                                'project': output['project'],
                                'db_host': output['external_ip'],
                                'hostname': vm_ip,
                                'container': 'cloudforms-0',
                                'openshift_creds': {
                                    'hostname': provider_dict['hostname'],
                                    'username': ocp_creds['username'],
                                    'password': ocp_creds['password'],
                                    'ssh': {
                                        'username': ssh_creds['username'],
                                        'password': ssh_creds['password'],
                                    }
                                },
                            },
                        ],
                }
            else:
                output_data = {
                    'appliances':
                        [{'hostname': vm_ip}]
                }
            yaml_data = yaml.safe_dump(output_data, default_flow_style=False)
            outfile.write(yaml_data)

        # In addition to the outfile, drop the ip address on stdout for easy parsing
        print(yaml_data)


if __name__ == "__main__":
    args = parse_cmd_line()
    kwargs = dict(args._get_kwargs())
    sys.exit(main(**kwargs))
