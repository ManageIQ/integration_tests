#!/usr/bin/env python3
import json
import os.path
from datetime import datetime

import requests

from artifactor.plugins.post_result import test_report
from cfme.utils.conf import credentials
from cfme.utils.config_data import cfme_data
from cfme.utils.trackerbot import post_jenkins_result

job_name = os.environ['JOB_NAME']
number = int(os.environ['BUILD_NUMBER'])
date = str(datetime.now())

# no env var for build status, have to query Jenkins API directly and parse json
jenkins_url = cfme_data.jenkins.url
jenkins_user = credentials.get(cfme_data.jenkins.credentials).msgbus_username
jenkins_token = credentials.get(cfme_data.jenkins.credentials).msgbus_token
build_data_url = '/'.join([jenkins_url, 'job', job_name, 'lastBuild', 'api', 'json'])
build_data = requests.get(build_data_url,
                          verify=False,
                          auth=(jenkins_user, jenkins_token))
if build_data.status_code != 200:
    raise ValueError('Bad return status ({}) from jenkins lastBuild API url: {}'
                     .format(build_data.status_code, build_data_url))
else:
    build_data_json = build_data.json()

build_status = build_data_json.get('result')

stream = os.environ['stream']
template = os.environ['appliance_template']

if test_report.check():
    with test_report.open() as f:
        artifact_report = json.load(f)
else:
    raise RuntimeError('Unable to post to jenkins without test report: {} does not exist!'
                       .format(test_report.strpath))


post_vars = {'job_name': job_name,
             'number': number,
             'stream': stream,
             'date': date,
             'template': template,
             'build_status': build_status,
             'artifact_report': artifact_report}


print('calling trackerbot.post_jenkins_result with attributes: ')
for name, attr in post_vars.items():
    if name != 'artifact_report':
        print('    {}: {}'.format(name, attr))

# pack the result attr values into the jenkins post
post_jenkins_result(**post_vars)
