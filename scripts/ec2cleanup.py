import argparse
import sys
from datetime import datetime
from tabulate import tabulate

from utils.log import logger
from utils.path import log_path
from utils.providers import list_provider_keys, get_mgmt


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--exclude-volumes', nargs='+',
                        help='List of volumes, which should be excluded.')
    parser.add_argument('--exclude-eips', nargs='+',
                        help='List of EIPs, which should be '
                             'excluded. Allocation_id or public IP are allowed.')
    parser.add_argument('--exclude-elbs', nargs='+',
                        help='List of ELBs, which should be '
                             'excluded.')
    parser.add_argument("--output", dest="output", help="target file name, default "
                                                        "'cleanup_ec2.log' in utils.path.log_path",
                        default=log_path.join('cleanup_ec2.log').strpath)
    args = parser.parse_args()
    return args


def delete_disassociated_addresses(provider_mgmt, excluded_eips, output):
    ip_list = []
    provider_name = provider_mgmt.kwargs['name']
    try:
        for ip in provider_mgmt.get_all_disassociated_addresses():
            if ip.allocation_id:
                if excluded_eips and ip.allocation_id in excluded_eips:
                    print "  Excluding allocation ID: {}".format(ip.allocation_id)  # noqa
                    continue
                else:
                    ip_list.append([provider_name, ip.public_ip, ip.allocation_id])
                    provider_mgmt.release_vpc_address(alloc_id=ip.allocation_id)
            else:
                if excluded_eips and ip.public_ip in excluded_eips:
                    print "  Excluding IP: {}".format(ip.public_ip)  # noqa
                    continue
                else:
                    ip_list.append([provider_name, ip.public_ip, 'N/A'])
                    provider_mgmt.release_address(address=ip.public_ip)
        print "  Released Addresses: {}".format(ip_list)  # noqa
        with open(output, 'a+') as report:
            if ip_list:
                # tabulate ip_list and write it
                report.write(tabulate(tabular_data=ip_list,
                                      headers=['Provider Key', 'Public IP', 'Allocation ID'],
                                      tablefmt='orgtbl'))

    except Exception as e:
        print e


def delete_unattached_volumes(provider_mgmt, excluded_volumes, output):
    volume_list = []
    provider_name = provider_mgmt.kwargs['name']
    try:
        for volume in provider_mgmt.get_all_unattached_volumes():
            if excluded_volumes and volume.id in excluded_volumes:
                print "  Excluding volume id: {}".format(volume.id)  # noqa
                continue
            else:
                volume_list.append([provider_name, volume.id])
                volume.delete()
        print "  Deleted Volumes: {}".format(volume_list)  # noqa
        with open(output, 'a+') as report:
            if volume_list:
                # tabulate volume_list and write it
                report.write(tabulate(tabular_data=volume_list,
                                      headers=['Provider Key', 'Volume ID'],
                                      tablefmt='orgtbl'))
    except Exception as e:
        logger.error(e)


def delete_unused_loadbalancers(provider_mgmt, excluded_elbs, output):
    elb_list = []
    provider_name = provider_mgmt.kwargs['name']
    try:
        for elb in provider_mgmt.get_all_unused_loadbalancers():
            if excluded_elbs and elb.name in excluded_elbs:
                print "  Excluding Elastic LoadBalancer id: {}".format(elb.name)  # noqa
                continue
            else:
                elb_list.append([provider_name, elb.name])
                provider_mgmt.delete_loadbalancer(loadbalancer=elb)
        print "  Deleted Elastic LoadBalancers: {}".format(elb_list)  # noqa
        with open(output, 'a+') as report:
            if elb_list:
                # tabulate volume_list and write it
                report.write(tabulate(tabular_data=elb_list,
                                      headers=['Provider Key', 'ELB name'],
                                      tablefmt='orgtbl'))
    except Exception as e:
        logger.error(e)


def ec2cleanup(exclude_volumes, exclude_eips, exclude_elbs, output):
    with open(output, 'w') as report:
        report.write('ec2cleanup.py, Address and Volume Cleanup')
        report.write("\nDate: {}\n".format(datetime.now()))
    for provider_key in list_provider_keys('ec2'):
        provider_mgmt = get_mgmt(provider_key)
        print "----- Provider: {} -----".format(provider_key)  # noqa
        print "Releasing addresses..."  # noqa
        delete_disassociated_addresses(provider_mgmt=provider_mgmt,
                                       excluded_eips=exclude_eips,
                                       output=output)
        print "Deleting volumes..."  # noqa
        delete_unattached_volumes(provider_mgmt=provider_mgmt,
                                  excluded_volumes=exclude_volumes,
                                  output=output)
        print "Deleting Elastic LoadBalancers..."  # noqa
        delete_unused_loadbalancers(provider_mgmt=provider_mgmt,
                                  excluded_elbs=exclude_elbs,
                                  output=output)

if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(ec2cleanup(args.exclude_volumes, args.exclude_eips, args.exclude_elbs, args.output))
