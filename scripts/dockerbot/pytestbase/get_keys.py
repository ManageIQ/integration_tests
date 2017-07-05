#!/cfme_pristine_venv/bin/python2
from __future__ import absolute_import
try:
    from cfme.utils import conf
except ImportError:
    from utils import conf
import subprocess
import sys

key_list = [key[-9:].replace(' ', '') for key in conf['gpg']['allowed_keys']]

proc = subprocess.Popen(['gpg', '--recv-keys'] + key_list)
proc.wait()
sys.exit(proc.returncode)
