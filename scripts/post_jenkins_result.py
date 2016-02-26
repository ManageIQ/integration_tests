#!/usr/bin/env python2
import json
import os
import os.path
from datetime import datetime

from artifactor.plugins.post_result import test_report
from utils import read_env
from utils.path import project_path
from utils.trackerbot import post_jenkins_result

job_name = os.environ['JOB_NAME']
number = int(os.environ['BUILD_NUMBER'])
date = str(datetime.now())

# reduce returns to bools for easy logic
runner_src = read_env(project_path.join('.jenkins_runner_result'))
runner_return = runner_src.get('RUNNER_RETURN', '1') == '0'
test_return = runner_src.get('TEST_RETURN', '1') == '0'


# 'stream' environ is set by jenkins for all stream test jobs
# but not in the template tester
if job_name not in ('template-tester', 'template-tester-openstack',
                    'template-tester-rhevm', 'template-tester-virtualcenter'):
    # try to pull out the appliance template name
    template_src = read_env(project_path.join('.appliance_template'))
    template = template_src.get('appliance_template', 'Unknown')
    stream = os.environ['stream']
else:
    tester_src = read_env(project_path.join('.template_tester'))
    stream = tester_src['stream']
    template = tester_src['appliance_template']

if test_report.check():
    with test_report.open() as f:
        artifact_report = json.load(f)
else:
    raise RuntimeError('Unable to post to jenkins without test report: '
        '{} does not exist!'.format(test_report.strpath))

if runner_return and test_return:
    build_status = 'success'
elif runner_return:
    build_status = 'unstable'
else:
    build_status = 'failed'

result_attrs = ('job_name', 'number', 'stream', 'date', 'template',
    'build_status', 'artifact_report')

# pack the result attr values into the jenkins post
post_jenkins_result(*[eval(attr) for attr in result_attrs])

# vain output padding calculation
# get len of longest string, pad with an extra space to make the output pretty
max_len = len(max(result_attrs, key=len)) + 1

# now print all the attrs so we can see what we posted (and *that* we
# posted) in the jenkins log
for attr in result_attrs[:-1]:
    print('{:>{width}}: {}'.format(attr, eval(attr), width=max_len))
