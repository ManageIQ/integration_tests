#!/usr/bin/env python2
from __future__ import print_function
import os
import sys

from cfme.utils import safe_string
from cfme.utils.trackerbot import post_task_result

with open("{}/setup.txt".format(os.environ['ARTIFACTOR_DIR'])) as f:
    data = f.read()

coverage = 0.0
try:
    with open("{}/coverage_result.txt".format(os.environ['CFME_REPO_DIR'])) as f:
        data = f.read().strip("\n")
    coverage = float(data)
except:
    pass

print(sys.argv[1], sys.argv[2], coverage)
post_task_result(sys.argv[1], sys.argv[2], safe_string(data), coverage)
