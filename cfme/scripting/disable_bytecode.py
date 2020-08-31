#!/usr/bin/env python3
from os import path

from cfme.utils.log import logger


DISABLE_BYTECODE = "import sys\nsys.dont_write_bytecode = True\n"


def ensure_file_contains(target, content):
    if path.exists(target):
        with open(target) as fp:
            if content not in fp.read():
                print(f'{target!r} has unexpected content')
                print('please open the file and add the following:')
                print(content)
                print("# end")
    else:
        with open(target, 'w') as fp:
            fp.write(content)


if __name__ == '__main__':
    try:
        import site
        site_packages = site.getsitepackages()[0]
        print(site_packages)
        target = path.join(site_packages, 'sitecustomize.py')
        ensure_file_contains(target, content=DISABLE_BYTECODE)
    except AttributeError:
        logger.warning('bytecode NOT disabled, site.getsitepackages not found.'
                       'Something is wrong with the site module, due to virtualenv creation.')
