#!/cfme_pristine_venv/bin/python2
from __future__ import print_function
import sys

try:
    from cfme.utils import safe_string
    from cfme.utils.trackerbot import post_task_result
    from cfme.utils.path import log_path
except ImportError:
    from utils import safe_string
    from utils.trackerbot import post_task_result
    from utils.path import log_path

setup_data = log_path.join("setup.txt").read()

coverage = 0.0
try:

    with log_path.join("coverage_result.txt").open() as f:
        coverage_data = f.read().strip("\n")
    coverage = float(coverage_data)
except Exception as e:
    print(e)

print(sys.argv[1], sys.argv[2], coverage)
post_task_result(sys.argv[1], sys.argv[2], safe_string(setup_data), coverage)
