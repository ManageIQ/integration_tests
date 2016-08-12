#!/usr/bin/env python2

from __future__ import unicode_literals
from functools32 import lru_cache
import requests
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
from utils.path import template_path, log_path
from utils.conf import jenkins


@lru_cache()
def get_json(run):
    r = requests.get(jenkins['url'].format(run))
    json = r.json()
    return json

template_env = Environment(
    loader=FileSystemLoader(template_path.strpath)
)

tests = defaultdict(dict)

runs = [(run['name'], run['ver']) for run in jenkins['runs']]

for run in runs:

    json = get_json(run[0])

    for case in json['suites'][0]['cases']:
        test_name = "{}/{}".format(case['className'], case['name'])
        tests[test_name][run[1]] = {'status': case['status'],
                                    'age': case['age']}

test_index = sorted(tests)

data = template_env.get_template('jenkins_report.html').render(tests=tests,
                                                               runs=runs, test_index=test_index)

f = open(log_path.strpath + '/jenkins.html', "w")
f.write(data)
f.close()
