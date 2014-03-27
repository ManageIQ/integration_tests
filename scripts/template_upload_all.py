#!/usr/bin/python

"""This script takes an url to a web directory containing links to CFME *.ova images, and runs
whatever uploader script is needed to upload the image & make a template from it. When this ends,
you should have template ready for deploying on respective providers.

This script takes only one parameter, which you can specify either by command-line argument, or
it can be found in cfme_data['basic_info'] section.

The scripts for uploading templates to providers can be also used standalone, with arguments in
cfme_data['template_upload'] and/or provided as a command-line arguments.

The scripts for respective providers are:
    - template_upload_rhevm.py
    - template_upload_rhos.py
    - template_upload_vsphere.py
"""

import argparse
import re
import yaml

from contextlib import closing
from urllib2 import urlopen

from utils.conf import cfme_data


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--dir_url', dest='dir_url',
                        help='URL of a web directory containing links to CFME images',
                        default=None)
    args = parser.parse_args()
    return args


def browse_directory(dir_url):
    name_dict = {}
    with closing(urlopen(dir_url)) as urlpath:
        string_from_url = urlpath.read()

    rhevm_pattern = re.compile('<a href="?\'?([^"\']*rhevm[^"\'>]*)')
    rhevm_image_name = rhevm_pattern.findall(string_from_url)
    rhos_pattern = re.compile('<a href="?\'?([^"\']*rhos[^"\'>]*)')
    rhos_image_name = rhos_pattern.findall(string_from_url)
    vsphere_pattern = re.compile('<a href="?\'?([^"\']*vsphere[^"\'>]*)')
    vsphere_image_name = vsphere_pattern.findall(string_from_url)

    if len(rhevm_image_name) is not 0:
        name_dict.update({'template_upload_rhevm':rhevm_image_name[0]})
    if len(rhos_image_name) is not 0:
        name_dict.update({'template_upload_rhos':rhos_image_name[0]})
    if len(vsphere_image_name) is not 0:
        name_dict.update({'template_upload_vsphere':vsphere_image_name[0]})

    if not dir_url.endswith('/'):
        dir_url = dir_url + '/'

    for key, val in name_dict.iteritems():
        name_dict[key] = dir_url + val

    return name_dict


if __name__ == "__main__":
    args = parse_cmd_line()

    dir_url = args.dir_url or cfme_data['basic_info']['cfme_images_url']

    dir_files = browse_directory(dir_url)

    for module in cfme_data['template_upload']:
        if module not in dir_files.iterkeys():
            continue

        kwargs = cfme_data['template_upload'][module]

        kwargs.update({'image_url':dir_files[module]})

        print "---Start of %s---" % module

        try:
            getattr(__import__(module), "run")(**kwargs)
        except:
            print "Exception: Module '%s' exitted with error." % module

        print "---End of %s---" % module
