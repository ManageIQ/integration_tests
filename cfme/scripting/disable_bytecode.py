#!/usr/bin/env python2
from __future__ import print_function
from os import path
import distutils


DISABLE_BYTECODE = "import sys\nsys.dont_write_bytecode = True\n"


def ensure_file_contains(target, content):
    if path.exists(target):
        with open(target) as fp:
            if content not in fp.read():
                print('{target!r} has unexpected content'.format(target=target))
                print('please open the file and add the following:')
                print(content)
                print("# end")
    else:
        with open(target, 'w') as fp:
            fp.write(content)


if __name__ == '__main__':
    site_packages = distutils.sysconfig_get_python_lib()
    target = path.join(site_packages, 'sitecustomize.py')
    ensure_file_contains(target, content=DISABLE_BYTECODE)
