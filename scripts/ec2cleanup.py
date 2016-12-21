import argparse
import datetime
import re
import sys
import time

from utils.log import logger
from utils.path import log_path
from utils.providers import list_providers, get_mgmt


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--max-hours', dest='maxhours', type=int, default=24,
                        help='Max hours since Instanced was created. (Default is 24 hours.)')
    parser.add_argument('--exclude-instances', nargs='+',
                        help='List of instances, which should be excluded.')
    parser.add_argument('--exclude-volumes', nargs='+',
                        help='List of volumes, which should be excluded.')
    parser.add_argument('--exclude-eips', nargs='+',
                        help='List of EIPs, which should be '
                             'excluded. Allocation_id or public IP are allowed.')
    parser.add_argument('text_to_match', nargs='*', default=None,
                        help='Regex in the name of vm to be affected, can be use multiple times'
                             "['^test_', '^jenkins', '^i-']")
    parser.add_argument("--output", dest="output", help="target file name",
                        default=log_path.join('ec2_instance_list.log').strpath)
    args = parser.parse_args()
    return args


def match(matchers, vm_name):
    for matcher in matchers:
        if matcher.match(vm_name):
            return True
    else:
        return False


def delete_old_instances(texts, ec2provider, provider_key, date,
                         maxhours, excluded_instances, output):
    deletetime = maxhours * 3600
    try:
        matchers = [re.compile(text) for text in texts]
        with open(output, 'a+') as report:
            print("\n{}:\n-----------------------\n".format(provider_key))
            report.write("\n{}:\n-----------------------\n".format(provider_key))
            for vm in ec2provider.list_vm(include_terminated=True):
                creation = ec2provider.vm_creation_time(vm)
                message = "EC2:{provider}  {instance}  \t {time} \t {instance_type} " \
                          "\t {instance_status}\n".format(provider=provider_key, instance=vm,
                                                          time=(date - creation),
                                                          instance_type=ec2provider.vm_type(vm),
                                                          instance_status=ec2provider.vm_status(vm))
                print(message)
                report.write(message)
                if excluded_instances and vm in excluded_instances:
                    continue
                if not match(matchers, vm):
                    continue
                difference = (date - creation).total_seconds()
                if difference >= deletetime:
                    ec2provider.delete_vm(instance_id=vm)
                    print("EC2:{}  {} is successfully deleted".format(provider_key, vm))
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


def ec2cleanup(texts, max_hours, exclude_instances, exclude_volumes, exclude_eips, output):
    for provider in list_providers('ec2'):
        ec2provider = get_mgmt(provider)
        logger.info("\n" + provider + ":\n")
        logger.info("Deleted instances:")
        delete_old_instances(texts=texts, ec2provider=ec2provider, provider_key=provider,
                             date=datetime.datetime.now(), maxhours=max_hours,
                             excluded_instances=exclude_instances, output=output)
        time.sleep(120)
        logger.info("\nReleased addresses:")
        delete_disassociated_addresses(ec2provider=ec2provider, excluded_eips=exclude_eips)
        logger.info("\nDeleted volumes:")
        delete_unattached_volumes(ec2provider=ec2provider, excluded_volumes=exclude_volumes)


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(ec2cleanup(args.text_to_match, args.maxhours, args.exclude_instances,
                        args.exclude_volumes, args.exclude_eips, args.output))
