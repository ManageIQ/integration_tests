#!/usr/bin/env python2
from utils.trackerbot import post_task_result
import os
import sys

with open("{}/setup.txt".format(os.environ['ARTIFACTOR_DIR'])) as f:
    data = f.read()

print sys.argv[1], sys.argv[2]
post_task_result(sys.argv[1], sys.argv[2], data)
