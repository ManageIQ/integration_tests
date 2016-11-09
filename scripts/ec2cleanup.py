from datetime import datetime
from utils.providers import list_providers, get_mgmt
import argparse
import sys
from time import sleep
from utils.log import logger


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--max-hours', dest='maxhours', type=int, default=24, help='Max hours '
        'since Instanced was created. (Default is 24 hours.)')
    parser.add_argument('--exclude-instances', nargs='+', help='List of instances, '
        'which should be excluded.')
    parser.add_argument('--exclude-volumes', nargs='+', help='List of volumes, which should be '
        'excluded.')
    parser.add_argument('--exclude-eips', nargs='+', help='List of EIPs, which should be '
        'excluded. Allocation_id or public IP are allowed.')
    args = parser.parse_args()
    return args


def delete_old_instances(ec2provider, date, maxhours, excluded_instances):
    deletetime = maxhours * 3600
    try:
        for instance in ec2provider.list_vm(include_terminated=True):
            if excluded_instances and instance in excluded_instances:
                continue
            else:
                creation = ec2provider.vm_creation_time(instance)
                difference = (date - creation).total_seconds()
                if (difference >= deletetime):
                    ec2provider.delete_vm(instance_id=instance)
    except Exception as e:
        logger.error(e)


def delete_disassociated_addresses(ec2provider, excluded_eips):
    try:
        for ip in ec2provider.get_all_disassociated_addresses():
            if ip.allocation_id:
                if excluded_eips and ip.allocation_id in excluded_eips:
                    continue
                else:
                    ec2provider.release_vpc_address(alloc_id=ip.allocation_id)
            else:
                if excluded_eips and ip.public_ip in excluded_eips:
                    continue
                else:
                    ec2provider.release_address(address=ip.public_ip)
    except Exception as e:
        logger.error(e)


def delete_unattached_volumes(ec2provider, excluded_volumes):
    try:
        for volume in ec2provider.get_all_unattached_volumes():
            if excluded_volumes and volume.id in excluded_volumes:
                continue
            else:
                volume.delete()
    except Exception as e:
        logger.error(e)


def ec2cleanup(max_hours, exclude_instances, exclude_volumes, exclude_eips):
    for provider in list_providers('ec2'):
        ec2provider = get_mgmt(provider)
        logger.info("\n" + provider + ":\n")
        logger.info("Deleted instances:")
        delete_old_instances(ec2provider=ec2provider, date=datetime.now(), maxhours=max_hours,
                             excluded_instances=exclude_instances)
        sleep(120)
        logger.info("\nReleased addresses:")
        delete_disassociated_addresses(ec2provider=ec2provider, excluded_ips=exclude_eips)
        logger.info("\nDeleted volumes:")
        delete_unattached_volumes(ec2provider=ec2provider, excluded_volumes=exclude_volumes)


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(ec2cleanup(args.max_hours, args.exclude_instances, args.exclude_volumes,
                        args.exclude_eips))
