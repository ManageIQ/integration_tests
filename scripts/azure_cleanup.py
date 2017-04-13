import argparse
import sys
import traceback as tb
from datetime import datetime

from utils.path import log_path
from utils.providers import list_provider_keys, get_mgmt


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--nic-template',
                        help='NIC Name template to be removed', default="test*", type=str)
    parser.add_argument('--pip-template',
                        help='PIP Name template to be removed', default="test*", type=str)
    parser.add_argument('--days',
                        help='days argument to find stack items older than X days ',
                        default="-7", type=str)
    parser.add_argument("--output", dest="output", help="target file name, default "
                                                        "'cleanup_azure.log' in "
                                                        "utils.path.log_path",
                        default=log_path.join('cleanup_azure.log').strpath)
    args = parser.parse_args()
    return args


def azure_cleanup(nic_template, pip_template, days, output):
    with open(output, 'w') as report:
        report.write('azure_cleanup.py, NICs and PIPs Cleanup')
        report.write("\nDate: {}\n".format(datetime.now()))
        try:
            for provider_key in list_provider_keys('azure'):
                provider_mgmt = get_mgmt(provider_key)
                nic_list = provider_mgmt.list_free_nics(nic_template)
                pip_list = provider_mgmt.list_free_pip(pip_template)
                stack_list = provider_mgmt.list_stack(days=days)
                report.write("----- Provider: {} -----".format(provider_key))
                if nic_list:
                    report.write("\nRemoving Nics with the name \"{}\":\n".format(nic_template))
                    report.write("\n".join(str(k) for k in nic_list))
                    provider_mgmt.remove_nics_by_search(nic_template)
                else:
                    report.write("\nNo \"{}\" NICs were found\n".format(nic_template))
                if pip_list:
                    report.write("\nRemoving Public IPs with the name \"{}\":\n".
                                 format(pip_template))
                    report.write("\n".join(str(k) for k in pip_list))
                    provider_mgmt.remove_pips_by_search(pip_template)
                else:
                    report.write("\nNo \"{}\" Public IPs were found\n".format(pip_template))
                if stack_list:
                    report.write(
                        "\nRemoving Stacks older than \"{}\" days: \n".format(days))
                    report.write("\n".join(str(k) for k in stack_list))
                    provider_mgmt.delete_stack_by_date(days=days)
                else:
                    report.write("\nNo stacks older than \"{}\" days were found\n".format(
                        days))
            return 0
        except Exception:
            print("Something bad happened during Azure cleanup")
            tb.print_exc()


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(azure_cleanup(args.nic_template, args.pip_template, args.days, args.output))
