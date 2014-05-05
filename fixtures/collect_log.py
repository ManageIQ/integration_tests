"""
logging:
   collect_log:
       enabled: True
       dir: video
       log_files:
           - /var/log/Xorg.0.log
           - /var/log/Xorg.1.log
"""

import os
import os.path
import pytest
import re

from utils.conf import env
from utils.path import log_path
import requests
import os

log_options = env.get('logging', {}).get('merkyl')
port = str(log_options.get('port', "8192"))


def get_path_and_file_name(node):
    """Extract filename and location from the node.

   Args:
       node: py.test collection node to examine.
   Returns: 2-tuple `(path, filename)`
   """
    log_name = re.sub(r"[^a-zA-Z0-9_.\-\[\]]", "_", node.name)  # Limit only sane characters
    log_name = re.sub(r"[/]", "_", log_name)                    # To be sure this guy don't get in
    log_name = re.sub(r"__+", "_", log_name)                    # Squash _'s to limit the length
    return node.parent.name, log_name


@pytest.mark.tryfirst
def pytest_configure():
    if log_options and log_options['enabled']:
        for log in log_options['log_files']:
            base, tail = os.path.split(log)

            try:
                url = env['base_url'].replace('https', 'http') + ":" + port + "/setup" + log
                requests.get(url)
            except:
                raise


def pytest_runtest_setup(item):
    if log_options and log_options['enabled']:
        try:
            url = env['base_url'].replace('https', 'http') + ":" + port + "/resetall"
            requests.get(url)
        except:
            raise


@pytest.mark.trylast
def pytest_runtest_teardown(item, nextitem):
    if log_options and log_options['enabled']:
        collect_log_path = log_path.join(log_options['dir'])
        log_dir, log_name = get_path_and_file_name(item)
        full_log_path = collect_log_path.join(log_dir)

        try:
            os.makedirs(str(full_log_path))
        except OSError:
            pass

        for log in log_options['log_files']:
            base, tail = os.path.split(log)
            filename = str(full_log_path.join(log_name)) + "-" + tail
            with open(filename, "w") as f:
                url = env['base_url'].replace('https', 'http') + ":" + port + "/get/" + tail
                try:
                    doc = requests.get(url)
                except:
                    doc = ""
                f.write(doc.content)


def pytest_unconfigure():
    if log_options and log_options['enabled']:
        for log in log_options['log_files']:
            base, tail = os.path.split(log)

            try:
                url = env['base_url'].replace('https', 'http') + ":" + port + "/delete/" + tail
                requests.get(url)
            except:
                raise
