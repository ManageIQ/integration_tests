#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_scvmm'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone SCVMM template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import sys
import os

from cfme.utils import trackerbot
from cfme.utils.providers import list_provider_keys
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.wait import wait_for
from wrapanapi.scvmm import SCVMMSystem

add_stdout_handler(logger)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--image_url', metavar='URL', dest="image_url",
                        help="URL of VHD", default=None)
    parser.add_argument('--library', dest="library",
                        help="SCVMM Library Destination", default=None)
    parser.add_argument('--provider', dest="provider",
                        help="Specify a SCVMM connection. --provider scvmm", default=None)
    parser.add_argument('--template_name', dest="template_name",
                        help="Override/Provide name of template", default=None)
    args = parser.parse_args()
    return args


def upload_vhd(client, url, library, vhd):

    logger.info("SCVMM: Downloading VHD file, then updating Library")

    script = """
        (New-Object System.Net.WebClient).DownloadFile("{}", "{}{}")
    """.format(url, library, vhd)
    logger.info(str(script))
    client.run_script(script)
    client.update_scvmm_library()


def make_template(client, host_fqdn, name, library, network, os_type, username_scvmm, cores, ram):

    logger.info("SCVMM: Adding HW Resource File and Template to Library")

    src_path = "{}{}.vhd".format(library, name)
    script = """
        $JobGroupId01 = [Guid]::NewGuid().ToString()
        $LogNet = Get-SCLogicalNetwork -Name \"{network}\"
        New-SCVirtualNetworkAdapter -JobGroup $JobGroupID01 -MACAddressType Dynamic `
            -LogicalNetwork $LogNet -Synthetic
        New-SCVirtualSCSIAdapter -JobGroup $JobGroupID01 -AdapterID 6 -Shared $False
        New-SCHardwareProfile -Name \"{name}\" -Owner \"{username_scvmm}\" `
            -Description 'Temp profile used to create a VM Template' -MemoryMB {ram} `
            -CPUCount {cores} -JobGroup $JobGroupID01
        $JobGroupId02 = [Guid]::NewGuid().ToString()
        $VHD = Get-SCVirtualHardDisk | where {{ $_.Location -eq \"{src_path}\" }} | `
            where {{ $_.HostName -eq \"{host_fqdn}\" }}
        New-SCVirtualDiskDrive -IDE -Bus 0 -LUN 0 -JobGroup $JobGroupID02 -VirtualHardDisk $VHD
        $HWProfile = Get-SCHardwareProfile | where {{ $_.Name -eq \"{name}\" }}
        $OS = Get-SCOperatingSystem | where {{ $_.Name -eq \"{os_type}\" }}
        New-SCVMTemplate -Name \"{name}\" -Owner \"{username_scvmm}\" -HardwareProfile $HWProfile `
            -JobGroup $JobGroupID02 -RunAsynchronously -Generation 1 -NoCustomization
        Remove-HardwareProfile -HardwareProfile \"{name}\"
    """.format(
        name=name,
        network=network,
        username_scvmm=username_scvmm,
        ram=ram,
        cores=cores,
        src_path=src_path,
        host_fqdn=host_fqdn,
        os_type=os_type)
    logger.info(str(script))
    client.run_script(script)


def check_kwargs(**kwargs):

    # If we don't have an image url, we're done.
    url = kwargs.get('image_url')
    if url is None:
        logger.info("SCVMM - There is nothing we can do without an image url set.  See help.")
        sys.exit(127)

    # If we don't have an provider, we're done.
    provider = kwargs.get('provider')
    if provider is None:
        logger.info("SCVMM - There is nothing we can do without a provider set.  See help.")
        sys.exit(127)


def make_kwargs(args, **kwargs):
    args_kwargs = dict(args._get_kwargs())

    if len(kwargs) is 0:
        return args_kwargs

    for kkey, kval in kwargs.iteritems():
        for akey, aval in args_kwargs.iteritems():
            if aval is not None:
                if kkey == akey:
                    if kval != aval:
                        kwargs[akey] = aval

    for akey, aval in args_kwargs.iteritems():
        if akey not in kwargs.iterkeys():
            kwargs[akey] = aval

    return kwargs


def make_kwargs_scvmm(cfme_data, provider, image_url, template_name):
    data = cfme_data['management_systems'][provider]

    tenant_id = data['template_upload'].get('tenant_id')

    scvmm_kwargs = cfme_data['template_upload']['template_upload_scvmm']

    final_kwargs = {'provider': provider}
    for kkey, kvalue in scvmm_kwargs.iteritems():
        final_kwargs[kkey] = kvalue
    final_kwargs['image_url'] = image_url
    final_kwargs['template_name'] = template_name
    if tenant_id:
        final_kwargs['tenant_id'] = tenant_id

    return final_kwargs


def run(**kwargs):

    for provider in list_provider_keys("scvmm"):

        kwargs = make_kwargs_scvmm(cfme_data, provider,
                                   kwargs.get('image_url'), kwargs.get('template_name'))
        check_kwargs(**kwargs)
        mgmt_sys = cfme_data['management_systems'][provider]
        host_fqdn = mgmt_sys['hostname_fqdn']
        creds = credentials[mgmt_sys['credentials']]

        # For powershell to work, we need to extract the User Name from the Domain
        user = creds['username'].split('\\')
        if len(user) == 2:
            username_powershell = user[1]
        else:
            username_powershell = user[0]

        username_scvmm = creds['domain'] + "\\" + creds['username']

        scvmm_args = {
            "hostname": mgmt_sys['ipaddress'],
            "username": username_powershell,
            "password": creds['password'],
            "domain": creds['domain'],
            "provisioning": mgmt_sys['provisioning']
        }
        client = SCVMMSystem(**scvmm_args)

        url = kwargs.get('image_url')

        # Template name equals either user input of we extract the name from the url
        new_template_name = kwargs.get('template_name')
        if new_template_name is None:
            new_template_name = os.path.basename(url)[:-4]

        logger.info("SCVMM:%s Make Template out of the VHD %s", provider, new_template_name)

        # use_library is either user input or we use the cfme_data value
        library = kwargs.get('library', mgmt_sys['template_upload'].get('vhds', None))

        logger.info("SCVMM:%s Template Library: %s", provider, library)

        #  The VHD name changed, match the template_name.
        new_vhd_name = new_template_name + '.vhd'

        network = mgmt_sys['template_upload'].get('network', None)
        os_type = mgmt_sys['template_upload'].get('os_type', None)
        cores = mgmt_sys['template_upload'].get('cores', None)
        ram = mgmt_sys['template_upload'].get('ram', None)

        # Uses PowerShell Get-SCVMTemplate to return a list of  templates and aborts if exists.
        if not client.does_template_exist(new_template_name):
            if kwargs.get('upload'):
                logger.info("SCVMM:%s Uploading VHD image to Library VHD folder.", provider)
                upload_vhd(client, url, library, new_vhd_name)
            if kwargs.get('template'):
                logger.info("SCVMM:%s Make Template out of the VHD %s", provider, new_template_name)

                make_template(
                    client,
                    host_fqdn,
                    new_template_name,
                    library,
                    network,
                    os_type,
                    username_scvmm,
                    cores,
                    ram
                )
            try:
                wait_for(lambda: client.does_template_exist(new_template_name),
                         fail_condition=False, delay=5)
                logger.info("SCVMM:%s template %s uploaded success", provider, new_template_name)
                logger.info("SCVMM:%s Add template %s to trackerbot", provider, new_template_name)
                trackerbot.trackerbot_add_provider_template(kwargs.get('stream'),
                                                            provider,
                                                            kwargs.get('template_name'))
            except Exception:
                logger.exception("SCVMM:%s Exception verifying the template %s",
                                 provider, new_template_name)
        else:
            logger.info("SCVMM: A Template with that name already exists in the SCVMMLibrary")


if __name__ == "__main__":
    logger.info("Start SCVMM Template upload")
    args = parse_cmd_line()
    logger.info("Args: %s", str(args))
    kwargs = cfme_data['template_upload']['template_upload_scvmm']

    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
