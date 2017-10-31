#!/usr/bin/env python2
"""Clone a template on a given provider to a VM instance

Where possible, defaults will come from cfme_data"""
import argparse
import sys

from cfme.utils.appliance import Appliance, IPAppliance
from cfme.utils.conf import cfme_data, credentials as cred, provider_data
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.path import log_path
from cfme.utils.providers import get_mgmt
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
            vm_deleted = provider_mgmt.delete_vm(vm_name)
            if vm_deleted:
                logger.info('VM %s destroyed', vm_name)
            else:
                logger.error('Destroying VM %s failed for unknown reasons', vm_name)
            return vm_deleted
    except Exception as e:
        logger.error('%s destroying VM %s (%s)', type(e).__name__, vm_name, str(e))


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
        flavors = provider_dict['template_upload'].get('flavors', ['m1.medium'])
        provider_type = provider_data['management_systems'][kwargs['provider']]['type']
        deploy_args = {
            'vm_name': kwargs['vm_name'],
            'template': kwargs['template'],
        }
    else:
        provider = get_mgmt(kwargs['provider'])
        provider_dict = cfme_data['management_systems'][kwargs['provider']]
        provider_type = provider_dict['type']
        flavors = cfme_data['appliance_provisioning']['default_flavors'].get(provider_type, [])
        deploy_args = {
            'vm_name': kwargs['vm_name'],
            'template': kwargs['template'],
        }

    logger.info('Connecting to {}'.format(kwargs['provider']))

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
            flavor = kwargs.get('flavor') or flavors[0]
        except IndexError:
            raise Exception('--flavor is required for EC2 instances and default is not set')
        deploy_args['instance_type'] = flavor
    elif provider_type == 'openstack':
        # filter openstack flavors based on what's available
        available_flavors = provider.list_flavor()
        flavors = filter(lambda f: f in available_flavors, flavors)
        try:
            flavor = kwargs.get('flavor') or flavors[0]
        except IndexError:
            raise Exception('--flavor is required for RHOS instances and '
                            'default is not set or unavailable on provider')
        # flavour? Thanks, psav...
        deploy_args['flavour_name'] = flavor

        if 'network' in provider_dict:
            # support rhos4 network names
            deploy_args['network_name'] = provider_dict['network']

        provider_pools = [p.name for p in provider.api.floating_ip_pools.list()]
        try:
            # TODO: If there are multiple pools, have a provider default in cfme_data
            floating_ip_pool = kwargs.get('floating_ip_pool') or provider_pools[0]
        except IndexError:
            raise Exception('No floating IP pools available on provider')

        if floating_ip_pool is not None:
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
    # Do it!
    try:
        logger.info('Cloning {} to {} on {}'.format(deploy_args['template'], deploy_args['vm_name'],
                                                    kwargs['provider']))
        provider.deploy_template(**deploy_args)
    except Exception as e:
        logger.exception(e)
        logger.error('provider.deploy_template failed')
        if kwargs.get('cleanup'):
            logger.info('attempting to destroy {}'.format(deploy_args['vm_name']))
            destroy_vm(provider, deploy_args['vm_name'])
        return 12

    if not provider.does_vm_exist(deploy_args['vm_name']):
        logger.error('provider.deploy_template failed without exception')
        return 12

    if provider.is_vm_running(deploy_args['vm_name']):
        logger.info("VM {} is running".format(deploy_args['vm_name']))
    else:
        logger.error("VM is not running")
        return 10

    try:
        ip, time_taken = wait_for(provider.get_ip_address, [deploy_args['vm_name']], num_sec=1200,
                                  fail_condition=None)
        logger.info('IP Address returned is {}'.format(ip))
    except Exception as e:
        logger.exception(e)
        logger.error('IP address not returned')
        return 10

    try:
        if kwargs.get('configure'):
            logger.info('Configuring appliance, this can take a while.')
            if kwargs.get('deploy'):
                app = IPAppliance(address=ip)
            else:
                app = Appliance(kwargs['provider'], deploy_args['vm_name'])
            if provider_type == 'gce':
                with app as ipapp:
                    ipapp.configure_gce()
            else:
                app.configure()
            logger.info('Successfully Configured the appliance.')
    except Exception as e:
        logger.exception(e)
        logger.error('Appliance Configuration Failed')
        if not kwargs.get('deploy'):
            app = Appliance(kwargs['provider'], deploy_args['vm_name'])
            ssh_client = app.ssh_client()
            status, output = ssh_client.run_command('find /root/anaconda-post.log')
            if status == 0:
                ssh_client.get_file('/root/anaconda-post.log',
                                    log_path.join('anaconda-post.log').strpath)
            ssh_client.close()
        return 10

    if kwargs.get('outfile') or kwargs.get('deploy'):
        with open(kwargs['outfile'], 'w') as outfile:
            outfile.write("appliance_ip_address={}\n".format(ip))

    # In addition to the outfile, drop the ip address on stdout for easy parsing
    print(ip)


if __name__ == "__main__":
    args = parse_cmd_line()
    kwargs = dict(args._get_kwargs())
    sys.exit(main(**kwargs))
