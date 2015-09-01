#!/usr/bin/env python2
"""Set up local NFS storage

Set up the RHCI deployer as the NFS storage for rhev

"""
import sys

from rhci_common import ssh_client
from utils.conf import rhci

if rhci.get('local_nfs_setup', None):
    client = ssh_client()
    res = client.run_command('fusor-local-nfs-setup')
    sys.exit(res.rc)
