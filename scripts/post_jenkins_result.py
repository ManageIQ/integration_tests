#!/usr/bin/env python2
from utils.trackerbot import post_jenkins_result
import os
import os.path
import xml.etree.ElementTree as ET
from datetime import datetime

xml_file = os.path.join(os.environ['WORKSPACE'], 'junit-report.xml')
# 'stream' environ is set by jenkins for all stream test jobs
# It will match the group name from the template tracker
stream = os.environ['stream']
number = int(os.environ['BUILD_NUMBER'])
build = os.environ.get('appliance_template', "Unknown")

date = str(datetime.now())

try:
    tree = ET.parse(xml_file)
    elem = tree.getroot()

    errors = int(elem.attrib['errors'])
    fails = int(elem.attrib['failures']) + errors
    skips = int(elem.attrib['skips'])
    tests = int(elem.attrib['tests'])
    passes = tests - (fails + errors)
except IOError:
    # junit-xml didn't exist, all the values become -1
    errors = fails = skips = tests = passes = -1

post_jenkins_result(number, stream, date, fails, skips, passes, build)
