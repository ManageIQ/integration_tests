import argparse
import sys
import traceback as tb
from datetime import datetime
from tabulate import tabulate

from cfme.utils.path import log_path
from cfme.utils.providers import list_provider_keys, get_mgmt


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--nic-template',
                        help='NIC Name template to be removed', default="test", type=str)
    parser.add_argument('--pip-template',
                        help='PIP Name template to be removed', default="test", type=str)
    parser.add_argument('--days-old',
                        help='--days-old argument to find stack items older than X days ',
                        default="7", type=int)
    parser.add_argument("--output", dest="output", help="target file name, default "
                                                        "'cleanup_azure.log' in "
                                                        "utils.path.log_path",
                        default=log_path.join('cleanup_azure.log').strpath)
    parser.add_argument('--remove-unused-blobs',
                        help='Removal of unused blobs', default=True)
    args = parser.parse_args()
    return args


def azure_cleanup(nic_template, pip_template, days_old, output):
    with open(output, 'w') as report:
        report.write('azure_cleanup.py, NICs, PIPs, Disks and Stack Cleanup')
        report.write("\nDate: {}\n".format(datetime.now()))
        try:
            for provider_key in list_provider_keys('azure'):
                provider_mgmt = get_mgmt(provider_key)
                nic_list = provider_mgmt.list_free_nics(nic_template)
                report.write("----- Provider: {} -----\n".format(provider_key))
                if nic_list:
                    report.write("\nRemoving Nics with the name \'{}\':\n".format(nic_template))
                    report.write(tabulate(tabular_data=[[nic] for nic in nic_list], headers=[
                        "Name"], tablefmt='orgtbl'))
                    provider_mgmt.remove_nics_by_search(nic_template)
                else:
                    report.write("No \'{}\' NICs were found\n".format(nic_template))
                pip_list = provider_mgmt.list_free_pip(pip_template)
                if pip_list:
                    report.write("\nRemoving Public IPs with the name \'{}\':\n".
                                 format(pip_template))
                    report.write(tabulate(tabular_data=[[pip] for pip in pip_list], headers=[
                        "Name"], tablefmt='orgtbl'))
                    provider_mgmt.remove_pips_by_search(pip_template)
                else:
                    report.write("No \'{}\' Public IPs were found\n".format(pip_template))
                stack_list = provider_mgmt.list_stack(days_old=days_old)
                if stack_list:
                    report.write("\nRemoving empty Stacks:\n")
                    removed_stacks = []
                    for stack in stack_list:
                        if provider_mgmt.is_stack_empty(stack):
                            removed_stacks.append(stack)
                            provider_mgmt.delete_stack(stack)
                    report.write(tabulate(tabular_data=[[st] for st in removed_stacks], headers=[
                        "Name"], tablefmt='orgtbl')) if len(removed_stacks) > 0 else None
                else:
                    report.write("\nNo stacks older than \'{}\' days were found\n".format(
                        days_old))

                """
                Blob removal section
                """
                report.write("\nRemoving 'bootdiagnostics-test*' containers\n")
                bootdiag_list = []
                for container in provider_mgmt.container_client.list_containers():
                    if container.name.startswith('bootdiagnostics-test'):
                        bootdiag_list.append(container.name)
                        provider_mgmt.container_client.delete_container(
                            container_name=container.name)
                report.write(tabulate(tabular_data=[[disk] for disk in bootdiag_list], headers=[
                    "Name"], tablefmt='orgtbl'))
                report.write("\nRemoving unused blobs and disks\n")
                removed_disks = provider_mgmt.remove_unused_blobs()
                if len(removed_disks['Managed']) > 0:
                    report.write('Managed disks:\n')
                    report.write(tabulate(tabular_data=removed_disks['Managed'], headers="keys",
                                          tablefmt='orgtbl'))
                if len(removed_disks['Unmanaged']) > 0:
                    report.write('\nUnmanaged blobs:\n')
                    report.write(tabulate(tabular_data=removed_disks['Unmanaged'], headers="keys",
                                          tablefmt='orgtbl'))
            return 0
        except Exception:
            report.write("Something bad happened during Azure cleanup\n")
            report.write(tb.format_exc())
            return 1


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(azure_cleanup(args.nic_template, args.pip_template, args.days_old, args.output))
