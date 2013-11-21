#!/bin/env python
import sys
import argparse
import logging
from utils.providers import provider_factory


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--provider', dest='provider_name',
        help='provider name in cfme_data')
    parser.add_argument('--template', help='the name of the template to clone')
    parser.add_argument('--vm_name', help='the name of the VM on which to act')
    parser.add_argument('--rhev_cluster', help='the name of the VM on which to act', default=None)
    parser.add_argument('--ec2_flavor', help='ec2 flavor', default=None)
    parser.add_argument('--rhos_flavor', help='rhos flavor', default=None)
    parser.add_argument('--rhos_floating_ip_pool', dest='ip_pool', default=None,
        help='openstack floating ip pool to use')
    parser.add_argument('--destroy', dest='destroy',
        help='Destroy the destination VM', action='store_true')
    parser.add_argument('--log', dest='loglevel',
        help='Set the log level', default='WARNING')

    args = parser.parse_args()

    # Set the logging level from the CLI
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.loglevel)
    logging.basicConfig(level=numeric_level)

    logging.info('Connecting to %s', args.provider_name)
    provider = provider_factory(args.provider_name)

    if args.destroy:
        try:
            if provider.does_vm_exist(args.vm_name):
                # Stop the vm first
                logging.warning('Destroying VM %s', args.vm_name)
                if provider.is_vm_running(args.vm_name):
                    provider.stop_vm(args.vm_name)
                status = provider.delete_vm(args.vm_name)
                if not status:
                    logging.error('Error destroying VM %s', args.vm_name)
                logging.info('VM %s destroyed', args.vm_name)
        except Exception as e:
            logging.error('Could not destroy VM %s (%s)', args.vm_name, e.message)
            return 11
    else:
        logging.info('Cloning %s to %s', args.template, args.vm_name)
        # passing unused args to ec2 provider would blow up so I
        #   had to make it a little more specific
        deply_args = {}
        if args.vm_name is not None:
            deply_args.update(vm_name=args.vm_name)
        if args.rhos_flavor is not None:
            deply_args.update(flavour_name=args.rhos_flavor)
        if args.ip_pool is not None:
            deply_args.update(assign_floating_ip=args.ip_pool)
        if args.rhev_cluster is not None:
            deply_args.update(cluster_name=args.rhev_cluster)
        if args.ec2_flavor is not None:
            deply_args.update(instance_type=args.ec2_flavor)

        vm = provider.deploy_template(args.template, **deply_args)
        if not provider.is_vm_running(vm):
            logging.error("VM is not running")
            return 10
        ip = provider.get_ip_address(vm)
        logging.info("VM " + vm + " is running")
        logging.info('IP Address returned is %s', ip)
        with open('vm.properties', 'w') as f:
            f.write("appliance_ip_address=%s\n" % ip)
            f.write("appliance_status=%s\n" % provider.vm_status(vm))
    return 0

if __name__ == "__main__":
    sys.exit(main())
