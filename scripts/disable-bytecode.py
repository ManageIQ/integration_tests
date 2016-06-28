#!/usr/bin/env python2
from os import path
import distutils

site_packages = distutils.sysconfig_get_python_lib()
target = path.join(site_packages, 'usercustomize.py')

content = "import sys\nsys.dont_write_bytecode = True\n"

if path.exists(target):
    with open(target) as fp:
        if content not in fp.read():
            print('%r has unexpected content' % target)
            print('please open the file and add the following:')
            print(content)
            print("# end")
else:
    with open(target, 'w') as fp:
        fp.write(content)
