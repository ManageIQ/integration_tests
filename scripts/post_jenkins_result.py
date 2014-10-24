#!/usr/bin/env python2
from utils.trackerbot import post_jenkins_result
import os
import os.path
import xml.etree.ElementTree as ET
from datetime import datetime

xml_file = os.path.join(os.environ['WORKSPACE'], 'junit-report.xml')
stream = os.environ['JOB_NAME'].replace('.', '').replace('-tests', '')
number = int(os.environ['BUILD_NUMBER'])

date = str(datetime.now())

tree = ET.parse(xml_file)
elem = tree.getroot()

errors = int(elem.attrib['errors'])
fails = int(elem.attrib['failures']) + errors
skips = int(elem.attrib['skips'])
tests = int(elem.attrib['tests'])
passes = tests - fails + errors

post_jenkins_result(number, stream, date, fails, skips, passes)
