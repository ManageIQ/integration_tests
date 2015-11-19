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

from utils.conf import cfme_data
from utils.conf import credentials
from mgmtsystem.scvmm import SCVMMSystem


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--image_url', metavar='URL', dest="image_url",
                        help="URL of VHD", default=None)
    parser.add_argument('--library', dest="library",
                        help="SCVMM Library Destination", default=None)
    parser.add_argument('--provider', dest="provider",
                        help="Specify a vCenter connection", default=None)
    parser.add_argument('--template_name', dest="template_name",
                        help="Override/Provide name of template", default=None)
    args = parser.parse_args()
    return args


def check_template_exists(client, name):
    if name in client.list_template():
        print "SCVMM: A Template with that name already exists in the SCVMMLibrary"
        return True
    else:
        return False


def upload_vhd(client, url, library, vhd):

    print "SCVMM: DOwnloading VHD file, then updating Library"

    script11 = "(New-Object System.Net.WebClient).DownloadFile( \
        '" + url + "', '" + library + vhd + "');"
    script11 += "$lib = Get-SCLibraryShare;"
    script11 += "$lib01 = $lib[1];"
    script11 += "Read-SCLibraryShare $lib01;"

    print "Invoke-Command -scriptblock {" + script11 + "}"
    client.run_script("Invoke-Command -scriptblock {" + script11 + "}")


def make_template(client, hostname, name, library, network, ostype, username_scvmm, cores, ram):
    src_path = library + name + ".vhd"
    print "SCVMM: Adding HW Resource File and Template to Library"
    script2 = "$JobGroupId01 = [Guid]::NewGuid().ToString();"
    script2 += "$LogNet = Get-SCLogicalNetwork -Name '" + network + "';"
    script2 += "New-SCVirtualNetworkAdapter -JobGroup $JobGroupID01 \
            -MACAddressType Dynamic -LogicalNetwork $LogNet;"
    script2 += "New-SCVirtualSCSIAdapter -JobGroup $JobGroupID01 -AdapterID 6 -Shared $False;"
    script2 += "New-SCHardwareProfile -Name '" + name + "' -Owner '" + username_scvmm + "' \
        -Description 'Temp profile used to create a VM Template' -MemoryMB  " + str(ram) + " \
            -CPUCount " + str(cores) + " -JobGroup $JobGroupID01;"
    script2 += "$JobGroupId02 = [Guid]::NewGuid().ToString();"
    script2 += "$VHD = Get-SCVirtualHardDisk | where {$_.Location -eq '" + src_path + "'} | \
                where {$_.HostName -eq 'scvmm2.cfme-qe-vmm-ad.rhq.lab.eng.bos.redhat.com'};"
    script2 += "New-SCVirtualDiskDrive -IDE -Bus 0 -LUN 0 "
    script2 += "-JobGroup $JobGroupID02 -VirtualHardDisk $VHD;"
    script2 += "$HWProfile = Get-SCHardwareProfile | where { $_.Name -eq '" + name + "' };"
    script2 += "$OS = Get-SCOperatingSystem | where "
    script2 += "{$_.Name -eq 'Red Hat Enterprise Linux 7 (64 bit)'};"
    script2 += "New-SCVMTemplate -Name '" + name + "' -Owner '" + username_scvmm + "' \
                -HardwareProfile $HWProfile -JobGroup $JobGroupID02 -ComputerName '*' \
                -JoinWorkgroup 'WORKGROUP' -OperatingSystem $OS -RunAsynchronously;"
    script2 += "Remove-HardwareProfile -HardwareProfile '" + name + "';"
    print "Invoke-Command -scriptblock {" + script2 + "}"
    client.run_script("Invoke-Command -scriptblock {" + script2 + "}")


def check_kwargs(**kwargs):

    # If we don't have an image url, we're done.
    url = kwargs.get('image_url', None)
    if url is None:
        print "SCVMM - There is nothing we can do without an image url set.  See help."
        sys.exit(127)

    # If we don't have an provider, we're done.
    provider = kwargs.get('provider', None)
    if provider is None:
        print "SCVMM - There is nothing we can do without a provider set.  See help."
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


def run(**kwargs):
    check_kwargs(**kwargs)
    provider = cfme_data['management_systems'][kwargs.get('provider')]
    hostname_fqdn = provider['hostname']
    creds = credentials[provider['credentials']]

    # For powershell to work, we need to extract the User Name from the Domain
    user = creds['username'].split('\\')
    if len(user) == 2:
        username_powershell = user[1]
    else:
        username_powershell = user[0]

    username_scvmm = creds['username']

    scvmm_args = {
        "hostname": provider['ipaddress'],
        "username": username_powershell,
        "password": creds['password'],
        "domain": creds['domain'],
    }
    client = SCVMMSystem(**scvmm_args)

    url = kwargs.get('image_url', None)

    # Template name equals either user input of we extract the name from the url
    new_template_name = kwargs.get('template_name', None)
    if new_template_name is None:
        new_template_name = os.path.basename(url)[:-4]

    print "Make Template out of the VHD " + new_template_name

    # use_library is either user input or we use the cfme_data value
    use_library = kwargs.get('library', None)
    if use_library is None:
        use_library = provider['template_upload'].get('library', None) + "\\VHDS\\"

    print "SCVMM: Template Library: %s" % use_library

    #  For now, we'll leave the VHD name as it is, but perhaps we'll add an argument option.
    new_vhd_name = os.path.basename(url)

    use_network = provider['template_upload'].get('network', None)
    use_os_type = provider['template_upload'].get('os_type', None)
    cores = provider['template_upload'].get('cores', None)
    ram = provider['template_upload'].get('ram', None)

    # Uses PowerShell Get-SCVMTemplate to return a list of  templates and aborts if exists.
    if not check_template_exists(client, new_template_name):
        if kwargs.get('upload'):
            upload_vhd(client, url, use_library, new_vhd_name)

        if kwargs.get('template'):
            print "Make Template out of the VHD " + new_template_name

            make_template(
                client,
                hostname_fqdn,
                new_template_name,
                use_library,
                use_network,
                use_os_type,
                username_scvmm,
                cores,
                ram
            )

    print "SCVMM: Completed successfully"


if __name__ == "__main__":
    print "Start SCVMM Template upload"
    args = parse_cmd_line()
    print "Args: " + str(args)
    kwargs = cfme_data['template_upload']['template_upload_scvmm']

    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
