#!/usr/bin/python

"""This takes cfme_data.yaml and all the template_upload_* scripts and runs them.
"""

import argparse
import yaml

from utils.conf import cfme_data


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('', dest='', help='', required=True)
    args = parser.parse_args()
    return args


def load_yaml(yaml_file):
    with open(yaml_file) as y:
        data = yaml.load(y)
    return data


if __name__ == "__main__":
    for test in cfme_data['template_upload']:
        module = test.keys()[0]
        kwargs = test[module]

        print "---Start of %s---" % module

        getattr(__import__(module), "run")(**kwargs)

        print "---End of %s---" % module
