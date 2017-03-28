import argparse
import sys
from datetime import datetime

from utils.path import log_path
from utils.providers import list_provider_keys, get_mgmt


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--nic-template',
                        help='NIC Name template to be removed', default="test*", type=str)
    parser.add_argument('--pip-template',
                        help='PIP Name template to be removed', default="test*", type=str)
    parser.add_argument("--output", dest="output", help="target file name, default "
                                                        "'cleanup_azure.log' in "
                                                        "utils.path.log_path",
                        default=log_path.join('cleanup_azure.log').strpath)
    args = parser.parse_args()
    return args


def azure_cleanup(nic_template, pip_template, output):
    with open(output, 'w') as report:
        report.write('azure_cleanup.py, NICs and PIPs Cleanup')
        report.write("\nDate: {}\n".format(datetime.now()))
    try:
        for provider_key in list_provider_keys('azure'):
            provider_mgmt = get_mgmt(provider_key)
            print "----- Provider: {} -----".format(provider_key)  # noqa
            print "Removing Nics with the name \"{}\"".format(nic_template)
            provider_mgmt.remove_unused_nics(nic_template)
            print "Removing Public IPs with the name \"{}\"".format(pip_template)
            provider_mgmt.remove_unused_pips(pip_template)
        return True
    except Exception as e:
        report.exception(e)
        report.error("Something happened to the Azure")
        return False

if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(azure_cleanup(args.nic_template,args.pip_template, args.output))
