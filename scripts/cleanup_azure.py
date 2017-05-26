#!/usr/bin/env python2

import argparse
import datetime
import sys

from utils.log import logger
from utils.providers import get_mgmt


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('-f', '--force', default=True, action='store_false', dest='prompt',
        help='Do not prompt before deleting VMs (danger zone!)')
    parser.add_argument('--max-hours', default=8,
        help='Max hours since the VM was created or last powered on '
        '(varies by provider, default 8)')
    parser.add_argument('text_to_match', nargs='*', default=['^test_', '^jenkins', '^i-'],
        help='Regex in the name of vm to be affected, can be use multiple times'
        ' (Defaults to "^test_" and "^jenkins")')
    args = parser.parse_args()
    return args


def remove_stale_vms(provider, resource_group, max_hours=8):
    logger.info("Beginning cleanup_azure_system check")
    vms = provider.list_vm_by_group(resource_group)
    logger.info("There are {} VMs, Beginning stale vm check and delete".format(len(vms)))
    logger.info("Max Hours: " + str(max_hours))
    for vm_name in vms:
        if vm_name[:4] == 'test':
            update_time = provider.vm_creation_time(vm_name, provider.resource_group)
            elapse_time = datetime.datetime.now() - update_time
            logger.info("STATUS vm {} uptime {}".format(vm_name, str(elapse_time.total_seconds())))
            logger.info("Max Hours: " + str(max_hours))
            if elapse_time.total_seconds() >= 10000:
                logger.info("Removing vm {} uptime {}".format(vm_name, str(elapse_time)))
                provider.delete_vm(vm_name, provider.resource_group)


def remove_orphan_vhds(provider):
    provider.run_script(
        """
        Invoke-Command -scriptblock {{
            -ErrorAction SilentlyContinue
            $key1 = \"{storage_key}\"
            $storageContext = New-AzureStorageContext -StorageAccountName \"{storage_account}\" `
            -StorageAccountKey $key1
            $storageContainer = Get-AzureStorageContainer -Context $storageContext
            $storageBlob = Get-AzureStorageBlob -Name \"{storage_container}\" `
            -Context $storageContext -Blob test_*
            foreach ($blob in $storageBlob) {{
                if ($blob.name -like 'test*'){{
                        Remove-AzureStorageBlob -Container "vhds" -Blob $blob.name `
                        -Context $storageContext -Force
                }}
            }}
        }}
        """.format(storage_account=provider.storage_account,
                   storage_key=provider.storage_key,
                   storage_container=provider.storage_container), True)


def remove_orphan_nics(provider):
    provider.run_script(
        """
        Invoke-Command -scriptblock {{
            $ni = Get-AzureRmNetworkInterface | Select Name
            foreach ($niname in $ni) {{
                if ($niname.name -like 'test*'){{
                        Remove-AzureRmNetworkInterface -Name $niname.name `
                        -ResourceGroupName \"{rg}\" -Force
                }}
            }}
        }}
        """.format(rg=provider.resource_group), True)


def remove_orphan_pips(provider):
    provider.run_script(
        """
        Invoke-Command -scriptblock {{
            $pi = Get-AzureRmPublicIpAddress | Select Name
            foreach ($piname in $pi) {{
                if ($piname.name -like 'test*'){{
                    Remove-AzureRmPublicIpAddress -Name $piname.name `
                    -ResourceGroupName \"{rg}\" -Force
                }}
            }}
        }}
        """.format(rg=provider.resource_group), True)


def remove_orphan_diags(provider):
    provider.run_script(
        """
        Invoke-Command -scriptblock {{
            -ErrorAction SilentlyContinue
            $key1 = \"{storage_key}\"
            $context = New-AzureStorageContext -StorageAccountName \"{storage_account}\" `
            -StorageAccountKey $key1
            $storageContainer = Get-AzureStorageContainer -Context $context
            foreach ($container in $storageContainer) {{
                if ($container.name -like 'bootdiagnostics-test*'){{
                    Remove-AzureStorageContainer -Container $container.name -Context $context -Force
                }}
            }}
        }}
        """.format(storage_account=provider.storage_account,
                   storage_key=provider.storage_key), True)


def cleanup_azure(texts, max_hours=8, prompt=True):
    logger.info("Max Hours: " + str(max_hours))
    provider = get_mgmt('azure')
    remove_stale_vms(provider, provider.resource_group, max_hours)
    remove_orphan_vhds(provider)
    remove_orphan_nics(provider)
    remove_orphan_pips(provider)
    remove_orphan_diags(provider)

if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(cleanup_azure(args.text_to_match, args.max_hours, args.prompt))
