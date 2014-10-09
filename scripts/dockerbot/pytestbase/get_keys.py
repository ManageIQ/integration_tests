#!/usr/bin/env python2
from utils import conf
import subprocess

key_list = []
for key in conf['gpg']['allowed_keys']:
    key_list.append(key[-9:].replace(' ', ''))
subprocess.Popen(['gpg', '--recv-keys'] + key_list)
