#!/usr/bin/env python3
from collections import defaultdict

import requests
from jinja2 import Environment
from jinja2 import FileSystemLoader

from cfme.utils.conf import jenkins
from cfme.utils.path import log_path
from cfme.utils.path import template_path


def get_json(run):
    r = requests.get(jenkins['url'].format(run))
    json = r.json()
    return json


template_env = Environment(
    loader=FileSystemLoader(template_path.strpath)
)

tests = defaultdict(dict)

runs = [(run['name'], run['ver']) for run in jenkins['runs']]

for run, ver in sorted(runs):

    json = get_json(run[0])

    for case in json['suites'][0]['cases']:
        test_name = "{}/{}".format(case['className'], case['name'])
        tests[test_name][ver] = {
            'status': case['status'],
            'age': case['age']}

test_index = sorted(tests)

data = template_env.get_template('jenkins_report.html').render(tests=tests,
                                                               runs=runs, test_index=test_index)

f = open(log_path.strpath + '/jenkins.html', "w")
f.write(data)
f.close()
