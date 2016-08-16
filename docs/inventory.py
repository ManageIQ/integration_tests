"""Dumps intersphinx inventorys to stdout to easily find intersphinx refs

You probably want to pipe this to a pager.

"""
from __future__ import unicode_literals
import os
import sys

from sphinx.ext import intersphinx

from conf import intersphinx_mapping


class App(object):
    # Fake app for passing to fetch_inventory
    srcdir = '.'

    def __init__(self, package_name):
        self.name = package_name

    def warn(self, msg):
        print(msg)


def main():
    for package_name, (uri, inv) in intersphinx_mapping.items():
        if inv is None:
            inv = 'objects.inv'
        inv_uri = os.path.join(uri, inv)
        app = App(package_name)
        inventory = intersphinx.fetch_inventory(app, '', inv_uri)
        for k in inventory.keys():
            print("{} {}".format(app.name, k))
            for name, value in inventory[k].items():
                print("{} {} is <{}:{}>".format(k, value[2], app.name, name))

if __name__ == "__main__":
    sys.exit(main())
