#!/usr/bin/env python2
from utils import conf
from time import sleep
import subprocess

key_list = []
for key in conf['gpg']['allowed_keys']:
    key_list.append(key[-9:].replace(' ', ''))

for attempt in range(0, 10):
    proc = subprocess.Popen(['gpg', '--recv-keys'] + key_list)
    proc.wait()
    if proc.returncode == 0:
        break
    sleep(5)
