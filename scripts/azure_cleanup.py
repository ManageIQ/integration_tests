import argparse
import logging
import sys
import traceback as tb
from datetime import datetime

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


def azure_cleanup(nic_template, pip_template, days_old):
        logger.info('azure_cleanup.py, NICs, PIPs, Disks and Stack Cleanup')
        logger.info("Date: {}".format(datetime.now()))
        try:
            for prov_key in list_provider_keys('azure'):
                logger.info("----- Provider: {} -----".format(prov_key))
                mgmt = get_mgmt(prov_key)
                mgmt.logger = logger
                for name, scr_id in mgmt.list_subscriptions():
                    logger.info("Subscription '{s}' is chosen".format(s=name))
                    setattr(mgmt, 'subscription_id', scr_id)
                    for resource_group in mgmt.list_resource_groups():
                        mgmt.logger.info('Checking "{}" resource group:'.format(resource_group))

                        # removing stale nics
                        mgmt.remove_nics_by_search(nic_template, resource_group)

                        # removing public ips
                        mgmt.remove_pips_by_search(pip_template, resource_group)

                        # removing stale stacks
                        stack_list = mgmt.list_stack(resource_group=resource_group,
                                                     days_old=days_old)
                        if stack_list:
                            removed_stacks = []
                            for stack in stack_list:
                                if mgmt.is_stack_empty(stack, resource_group=resource_group):
                                    removed_stacks.append(stack)
                                    mgmt.delete_stack(stack, resource_group)

                            if not removed_stacks:
                                logger.info("No empty stacks older '{}' days were found".format(
                                    days_old))
                        mgmt.remove_unused_blobs(resource_group)

            return 0
        except Exception:
            logger.info("Something bad happened during Azure cleanup")
            logger.info(tb.format_exc())
            return 1


if __name__ == "__main__":
    args = parse_cmd_line()

    # setup logging
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    file_handler = logging.FileHandler(args.output)
    file_handler.setFormatter(formatter)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)

    sys.exit(azure_cleanup(args.nic_template, args.pip_template, args.days_old))
