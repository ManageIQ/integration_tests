#!/usr/bin/env python2
from cfme.utils import conf
import subprocess
import sys

key_list = [key[-9:].replace(' ', '') for key in conf['gpg']['allowed_keys']]

proc = subprocess.Popen(['gpg', '--recv-keys'] + key_list)
proc.wait()
sys.exit(proc.returncode)
