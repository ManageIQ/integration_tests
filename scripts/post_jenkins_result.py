#!/usr/bin/env python2
import os
import os.path
import xml.etree.ElementTree as ET
from datetime import datetime

from utils import read_env
from utils.path import project_path
from utils.trackerbot import post_jenkins_result

xml_file = os.path.join(os.environ['WORKSPACE'], 'junit-report.xml')
# 'stream' environ is set by jenkins for all stream test jobs
# It will match the group name from the template tracker
stream = os.environ['stream']
job_name = os.environ['JOB_NAME']
number = int(os.environ['BUILD_NUMBER'])

date = str(datetime.now())

try:
    tree = ET.parse(xml_file)
    elem = tree.getroot()

    errors = int(elem.attrib['errors'])
    fails = int(elem.attrib['failures']) + errors
    skips = int(elem.attrib['skips'])
    # junit report doesn't count skips as tests
    tests = int(elem.attrib['tests']) + skips + errors
    passes = tests - (skips + fails)
except IOError:
    # junit-xml didn't exist, all the values become -1
    errors = fails = skips = tests = passes = -1

# reduce returns to bools for easy logic
runner_src = read_env(project_path.join('.jenkins_runner_result'))
print runner_src
runner_return = runner_src.get('RUNNER_RETURN', '1') == '0'
test_return = runner_src.get('TEST_RETURN', '1') == '0'
print runner_return, test_return

# try to pull out the appliance template name
template_src = read_env(project_path.join('.appliance_template'))
template = template_src.get('appliance_template', 'Unknown')

if runner_return and test_return:
    build_status = 'success'
elif runner_return:
    build_status = 'unstable'
else:
    build_status = 'failed'

result_attrs = ('job_name', 'number', 'stream', 'date', 'fails',
    'skips', 'passes', 'template', 'build_status')

# pack the result attr values into the jenkins post
post_jenkins_result(*[eval(attr) for attr in result_attrs])

# vain output padding calculation
# get len of longest string, pad with an extra space to make the output pretty
max_len = len(max(result_attrs, key=len)) + 1

# now print all the attrs so we can see what we posted (and *that* we
# posted) in the jenkins log
for attr in result_attrs:
    print '{:>{width}}: {}'.format(attr, eval(attr), width=max_len)
