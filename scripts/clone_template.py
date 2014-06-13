#!/usr/bin/env python2
import argparse
import sys

from utils.log import logger
from utils.providers import provider_factory
from utils.wait import wait_for


def destroy(provider, args):
    try:
        if provider.does_vm_exist(args.vm_name):
            # Stop the vm first
            logger.warning('Destroying VM %s', args.vm_name)
            if provider.is_vm_running(args.vm_name):
                provider.stop_vm(args.vm_name)
            if provider.delete_vm(args.vm_name):
                logger.info('VM %s destroyed', args.vm_name)
            else:
                logger.error('Error destroying VM %s', args.vm_name)
    except Exception as e:
        logger.error('Could not destroy VM %s (%s)', args.vm_name, e.message)
        sys.exit(11)


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--provider', dest='provider_name',
        help='provider name in cfme_data')
    parser.add_argument('--template', help='the name of the template to clone')
    parser.add_argument('--vm_name', help='the name of the VM on which to act')
    parser.add_argument('--rhev_cluster', help='the name of the VM on which to act', default=None)
    parser.add_argument('--rhev_place_policy_host', help='the host for the vm to start on',
        default=None)
    parser.add_argument('--rhev_place_policy_aff', help='the affinity of the vm on a host',
        default=None)
    parser.add_argument('--ec2_flavor', help='ec2 flavor', default=None)
    parser.add_argument('--rhos_flavor', help='rhos flavor', default=None)
    parser.add_argument('--rhos_floating_ip_pool', dest='ip_pool', default=None,
        help='openstack floating ip pool to use')
    parser.add_argument('--destroy', dest='destroy',
        help='Destroy the destination VM', action='store_true')
    parser.add_argument('--log', dest='loglevel',
        help='Set the log level', default='WARNING')
    parser.add_argument('--outfile', dest='outfile',
        help='Write provisioning details to the named file', default='')

    args = parser.parse_args()
    if not args.provider_name:
        parser.error('--provider is required')

    logger.info('Connecting to %s', args.provider_name)
    provider = provider_factory(args.provider_name)

    if args.destroy:
        destroy(provider, args)
    else:
        logger.info('Cloning %s to %s', args.template, args.vm_name)
        # passing unused args to ec2 provider would blow up so I
        #   had to make it a little more specific
        deploy_args = {}
        if args.vm_name is not None:
            deploy_args.update(vm_name=args.vm_name)
        if args.rhos_flavor is not None:
            deploy_args.update(flavour_name=args.rhos_flavor)
        if args.ip_pool is not None:
            deploy_args.update(assign_floating_ip=args.ip_pool)
        if args.rhev_cluster is not None:
            deploy_args.update(cluster_name=args.rhev_cluster)
        if args.rhev_place_policy_host is not None:
            deploy_args.update(placement_policy_host=args.rhev_place_policy_host)
        if args.rhev_place_policy_aff is not None:
            deploy_args.update(placement_policy_affinity=args.rhev_place_policy_aff)
        if args.ec2_flavor is not None:
            deploy_args.update(instance_type=args.ec2_flavor)

        try:
            vm_name = provider.deploy_template(args.template, **deploy_args)
        except:
            logger.exception(sys.exc_info()[0])
            destroy(provider, args)
            return 12

        if not provider.is_vm_running(vm_name):
            logger.error("VM is not running")
            return 10

        ip, time_taken = wait_for(provider.get_ip_address, [vm_name], num_sec=600,
                                  fail_condition=None)
        logger.info("VM " + vm_name + " is running")
        logger.info('IP Address returned is %s', ip)
        if args.outfile:
            with open(args.outfile, 'w') as outfile:
                outfile.write("appliance_ip_address=%s\n" % ip)
        # In addition to the outfile, drop the ip address on stdout for easy parsing
        print ip
    return 0

if __name__ == "__main__":
    sys.exit(main())
