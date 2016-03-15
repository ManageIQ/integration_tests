#!/usr/bin/env python2
"""Clone a template on a given provider to a VM instance

Where possible, defaults will come from cfme_data"""
import argparse
import sys

from utils.appliance import Appliance
from utils.conf import cfme_data
from utils.log import logger
from utils.providers import destroy_vm, get_mgmt
from utils.wait import wait_for


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    # required options (heh)
    parser.add_argument('--provider', help='provider key in cfme_data')
    parser.add_argument('--template', help='the name of the template to clone')
    parser.add_argument('--vm_name', help='the name of the VM to create')

    # generic options
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

    # get_mgmt validates, since it will explode without an existing key or type
    provider = get_mgmt(args.provider)
    provider_dict = cfme_data['management_systems'][args.provider]
    provider_type = provider_dict['type']

    # Used by the cloud provs
    flavors = cfme_data['appliance_provisioning']['default_flavors'].get(provider_type, [])

    logger.info('Connecting to {}'.format(args.provider))

    if args.destroy:
        # TODO: destroy should be its own script
        # but it's easy enough to just hijack the parser here
        # This returns True if destroy fails to give POSIXy exit codes (0 is good, False is 0, etc)
        return not destroy_vm(provider, args.vm_name)

    deploy_args = {
        'vm_name': args.vm_name,
        'template': args.template,
    }

    # Try to snag defaults from cfme_data here for each provider type
    if provider_type == 'rhevm':
        cluster = provider_dict.get('default_cluster', args.cluster)
        if cluster is None:
            raise Exception('--cluster is required for rhev instances and default is not set')
        deploy_args['cluster'] = cluster

        if args.place_policy_host and args.place_policy_aff:
            deploy_args['placement_policy_host'] = args.place_policy_host
            deploy_args['placement_policy_affinity'] = args.rhev_place_policy_aff
    elif provider_type == 'ec2':
        # ec2 doesn't have an api to list available flavors, so the first flavor is the default
        try:
            flavor = args.flavor or flavors[0]
        except IndexError:
            raise Exception('--flavor is required for EC2 instances and default is not set')
        deploy_args['instance_type'] = flavor
    elif provider_type == 'openstack':
        # filter openstack flavors based on what's available
        available_flavors = provider.list_flavor()
        flavors = filter(lambda f: f in available_flavors, flavors)
        try:
            flavor = args.flavor or flavors[0]
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
            floating_ip_pool = args.floating_ip_pool or provider_pools[0]
        except IndexError:
            raise Exception('No floating IP pools available on provider')

        if floating_ip_pool is not None:
            deploy_args['floating_ip_pool'] = floating_ip_pool
    elif provider_type == "virtualcenter":
        if "allowed_datastores" in provider_dict:
            deploy_args["allowed_datastores"] = provider_dict["allowed_datastores"]

    # Do it!
    try:
        logger.info('Cloning {} to {} on {}'.format(args.template, args.vm_name, args.provider))
        provider.deploy_template(**deploy_args)
    except Exception as e:
        logger.exception(e)
        logger.error('Clone failed')
        if args.cleanup:
            logger.info('attempting to destroy {}'.format(args.vm_name))
            destroy_vm(provider, args.vm_name)
            return 12

    if provider.is_vm_running(args.vm_name):
        logger.info("VM {} is running".format(args.vm_name))
    else:
        logger.error("VM is not running")
        return 10

    ip, time_taken = wait_for(provider.get_ip_address, [args.vm_name], num_sec=1200,
                              fail_condition=None)
    logger.info('IP Address returned is {}'.format(ip))

    if args.configure:
        logger.info('Configuring appliance, this can take a while.')
        app = Appliance(args.provider, args.vm_name)
        app.configure()

    if args.outfile:
        with open(args.outfile, 'w') as outfile:
            outfile.write("appliance_ip_address={}\n".format(ip))

    # In addition to the outfile, drop the ip address on stdout for easy parsing
    print(ip)

if __name__ == "__main__":
    sys.exit(main())
