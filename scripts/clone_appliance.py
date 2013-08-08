#!/bin/env python
import sys
import argparse
import logging
from common.mgmt_system import VMWareSystem

def main(argv=None):
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('source', metavar='source_template_name',
            help='The source template')
    parser.add_argument('dest', metavar='dest_vm_name')
    parser.add_argument('--vspherehost', dest='hostname',
            help='The vsphere host to connect to', required=True)
    parser.add_argument('--vsphereuser', dest='username',
            help='The vsphere user', required=True)
    parser.add_argument('--vspherepass', dest='password',
            help='The vsphere password', required=True)
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

    logging.info('Connecting to %s as %s', args.hostname, args.username)
    system = VMWareSystem(args.hostname, args.username, args.password)
    if args.destroy:
        logging.warning('Destroying VM %s', args.dest)
        try:
            # Stop the vm first
            if system.is_vm_running(args.dest):
                system.stop_vm(args.dest)
            status = system.delete_vm(args.dest)
            if not status:
                logging.error('Error destroying VM %s', args.dest)
            logging.info('VM %s destroyed', args.dest)
        except Exception as e:
            logging.error('Could not destroy VM %s (%s)', args.dest, e.message)
            return 11
    else:
        logging.info('Cloning %s to %s', args.source, args.dest)
        ip = system.clone_vm(args.source, args.dest)
        if not system.is_vm_running(args.dest):
            logging.error("VM is not running")
            return 10
        logging.debug("VM is running")
        logging.info('IP Address returned is %s', ip)
        with open('vm.properties', 'w') as f:
            f.write("appliance_ip_address=%s\n" % ip)
            f.write("appliance_status=%s\n" % system.vm_status(args.dest))
    return 0

if __name__ == "__main__":
    sys.exit(main())


