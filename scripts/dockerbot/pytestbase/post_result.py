#!/usr/bin/env python2
from utils.trackerbot import post_task_result
import os
import sys

with open("{}/setup.txt".format(os.environ['ARTIFACTOR_DIR'])) as f:
    data = f.read()

coverage = 0.0
try:
    with open("{}/coverage_result.txt".format(os.environ['CFME_REPO_DIR'])) as f:
        data = f.read().strip("\n")
    coverage = float(data)
except:
    pass

print sys.argv[1], sys.argv[2], coverage
post_task_result(sys.argv[1], sys.argv[2], data, coverage)
