#!/usr/bin/env python

"""Patch appliance.js on a running appliance with an ajax wait fix

The 'patch' utility must be installed for this script to work.

This should only be needed on appliances before version 5.2.2.

"""

import argparse
import atexit
import os
import shutil
import subprocess
import sys
from tempfile import mkdtemp
from utils.conf import credentials
from utils.datafile import data_path_for_filename
from utils.path import scripts_path
from utils.ssh import SSHClient


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')
    parser.add_argument('-R', '--reverse', help='flag to indicate the patch should be undone',
        action='store_true', default=False, dest='reverse')

    args = parser.parse_args()

    # Find the patch file
    patch_file_name = data_path_for_filename('ajax_wait.diff', scripts_path.strpath)

    # Set up temp dir
    tmpdir = mkdtemp()
    atexit.register(shutil.rmtree, tmpdir)
    source = '/var/www/miq/vmdb/public/javascripts/application.js'
    target = os.path.join(tmpdir, 'application.js')

    # Init SSH client
    ssh_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': args.address
    }
    client = SSHClient(**ssh_kwargs)

    print 'retriving appliance.js from appliance'
    client.get_file(source, target)

    os.chdir(tmpdir)
    # patch, level 4, patch direction (default forward), ignore whitespace, don't output rejects
    direction = '-N -R' if args.reverse else '-N'
    exitcode = subprocess.call('patch -p4 %s -l -r- < %s' % (direction, patch_file_name),
        shell=True)

    if exitcode == 0:
        # Put it back after successful patching.
        print 'replacing appliance.js on appliance'
        client.put_file(target, source)
    else:
        print 'not changing appliance'

    return exitcode


if __name__ == '__main__':
    sys.exit(main())
