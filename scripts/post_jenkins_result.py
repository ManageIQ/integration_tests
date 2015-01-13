#!/usr/bin/env python2
from utils.trackerbot import post_jenkins_result
import os
import os.path
import xml.etree.ElementTree as ET
from datetime import datetime
from textwrap import dedent

xml_file = os.path.join(os.environ['WORKSPACE'], 'junit-report.xml')
# 'stream' environ is set by jenkins for all stream test jobs
# It will match the group name from the template tracker
stream = os.environ['stream']
job_name = os.environ['JOB_NAME']
number = int(os.environ['BUILD_NUMBER'])
template = os.environ.get('appliance_template', "Unknown")

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

try:
    results = open('.jenkins-runner-result').read()
except IOError:
    # If we can't open the runner result, it probably wasn't written in
    # the first place, which means everything failed.
    results = dedent('''\
    RUNNER_RETURN=1
    TEST_RETURN=1
    ''')

runner_return = test_return = False
for line in results.splitlines():
    # reduce returns to bools for easy logic
    if line.startswith('RUNNER_RETURN'):
        runner_return = line.split('=')[1] == 0
    elif line.startswith('TEST_RETURN'):
        test_return = line.split('=')[1] == 0

if runner_return and test_return:
    build_status = 'success'
elif runner_return:
    build_status = 'unstable'
else:
    build_status = 'failed'

post_jenkins_result(job_name, number, stream, date, fails,
    skips, passes, template, build_status)
