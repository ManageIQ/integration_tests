from __future__ import unicode_literals
import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader
from utils.path import template_path, log_path, data_path
import re
import base64
import os
import shutil
import yaml
import copy


def create_groupings(input_list):
    output_list = []
    while True:
        output_list = []
        for params in input_list:
            for param_group in output_list:
                if set(params) & set(param_group):
                    [param_group.add(param) for param in param_group | set(params)]
                    break
            else:
                output_list.append(set(params))
        if len(input_list) == len(output_list):
            break
        input_list = output_list

    return output_list


class Suite(object):
    def __init__(self):
        pass


class Test(object):
    def __init__(self):
        self.results = []
        pass


class Group(object):
    def __init__(self, params):
        self.params = sorted(list(params))
        self.tests = []

with open(os.path.join(data_path.strpath, 'suite.yaml')) as f:
    suite_data = yaml.safe_load(f)


with open('doc_data.yaml') as f:
    doc_data = yaml.load(f)

tree = ET.parse('junit-report.xml')
elem = tree.getroot()

suites = []
prov_suites = {prov: list() for prov in suite_data['provider_keys']}
cache_suites = {}

for test_data in elem:
    if test_data.tag == 'testcase':
        item_class = test_data.attrib['classname']
        item_name = test_data.attrib['name']
        item_param = re.findall('\.*(\[.*\])', item_name)

        if item_param:
            item_name = item_name.replace(item_param[0], '')
            item_id_param = item_param[0].strip('[]')

        if item_class:
            node_name = '{}.{}'.format(item_class, item_name)
        else:
            node_name = item_name
        suite_name = doc_data.get(node_name, {}).get('metadata', {}).get('from_docs', {}) \
            .get('suite', None)
        if suite_name:
            suite_proper_name = suite_data.get(suite_name, {}).get('name', None)
            suite_description = suite_data.get(suite_name, {}).get('description', None)
        else:
            # suite_name = "zz" + item_class
            # suite_proper_name = item_class
            suite_name = "zz" + ".".join(node_name.split(".")[:-1])
            suite_proper_name = ".".join(node_name.split(".")[:-1])

            suite_description = "Unknown"
        # name = item_class.replace('cfme.tests', '')
        # suite_name = ".".join([p.capitalize() for p in name.split(".")][:-1])
        # suite_proper_name = "/".join([p.capitalize() for p in suite_name.split(".")])
        # suite_description = "Unknown"

        suite = cache_suites.get(suite_name, None)

        if not suite:
            suite = Suite()
            suite.name = suite_proper_name
            suite.tests = []
            suite.cache_params = []
            suite.description = suite_description
            suite.params = set(['No param'])
            suite.cache_tests = {}

        if item_param:
            suite.params.add(item_id_param)

        cache_suites[suite_name] = suite

        status = 'Passed'

        for element in test_data:
            if element.tag == 'failure':
                status = 'Failed'
            elif element.tag == 'skipped':
                status = 'Skipped'
            elif element.tag == 'error':
                status = 'Error'
            else:
                status = 'Passed'

        test = suite.cache_tests.get(node_name, None)
        if not test:
            test = Test()
            test.name = node_name
            test.link = test.name.replace('.', '')
            test.short_name = item_name
            try:
                docstring = base64.b64decode(doc_data[node_name]['docstring'])
            except:
                docstring = "Can't find docstring"
            test.description = docstring.split('\n')[0]
            test.docstring = '<br />\n'.join(docstring.splitlines())
            suite.cache_tests[node_name] = test

        if item_param:
            test.results.append((item_id_param, status))
        else:
            test.results.append(('Unparametrized', status))

# Iterate through the suite keys in order
for suite in sorted(cache_suites.keys()):
    # obtain the suite from the key
    this_suite = cache_suites[suite]
    # order the params
    this_suite.params = sorted(this_suite.params)
    # add the suite the _real_ list of suites, which will be ordered
    suites.append(this_suite)
    # iterate through the tests (sorted by the short_name)
    for test in sorted(this_suite.cache_tests.keys(),
                       key=lambda e: this_suite.cache_tests[e].short_name):
        # append to cache_params a list of all params for this test from the results
        this_suite.cache_params.append(
            [param for param, res in this_suite.cache_tests[test].results])
        # append to the suites tests list, the test itself
        this_suite.tests.append(this_suite.cache_tests[test])
    # create the unique sets of params
    this_suite.groups = [Group(group) for group in create_groupings(this_suite.cache_params)]
    # iterate through the tests (which will be sorted)
    for test in this_suite.tests:
        # find a list of params for this test
        params = set([param for param, res in test.results])
        # iterate through the groups in the suite to find which one to add to
        for group in this_suite.groups:
            # if the groups params intersect with the tests params, it must be the right group
            if params & set(group.params):
                # add the test to the group
                group.tests.append(test)


template_env = Environment(
    loader=FileSystemLoader(template_path.strpath)
)
data = template_env.get_template('test_matrix.html').render({'suites': suites})
with open(os.path.join(log_path.strpath, 'test_matrix.html'), "w") as f:
    f.write(data)

# iterate the suite_data provider_keys, vsphere, rhevm (basically iterate the prefixes)
# to create the sub pages
for prov in suite_data['provider_keys']:
    # iterate the suites
    for suite in suites:
        # iterate the groups in the suites
        for group in suite.groups:
            # iterate the params in the group
            for param in group.params:
                # if the param starts with the prov prefix from the outer most loop, continue
                if prov in param:
                    # iterate through the prov_suites, necessary to keep them in order
                    # could be done with an ordered dict, but.....meh it's 00:53 here
                    # we are searching to see if the suite is already added
                    for this_suite in prov_suites[prov]:
                        # if the suite names match;
                        if suite.name == this_suite.name:
                            # iterate the groups to see if one already exists
                            for the_group in this_suite.groups:
                                # if the groups intersect(they should be identical)
                                if set(group.params) & set(the_group.params):
                                    # the group is found and we die, leaving the_group to be used
                                    break
                            # if we finish the loop and no group is found, add it
                            else:
                                params = sorted([param for param in group.params if prov in param])
                                the_group = Group(params)
                                this_suite.groups.append(the_group)
                            # break here as the suite is found and has the right group now
                            break
                    # If the suite is not found, then we create it, and the group
                    else:
                        the_suite = copy.deepcopy(suite)
                        prov_suites[prov].append(the_suite)
                        the_suite.groups = []
                        params = sorted([param for param in group.params if prov in param])
                        the_group = Group(params)
                        the_suite.groups.append(the_group)
                    # once we are sure we have the right suite and group, we simple append the
                    # test to the suites groups
                    # darn jinja needing data in the right format
                    the_tests = copy.deepcopy(group.tests)
                    the_group.tests = the_tests
    # write the page for the specific prov
    data = template_env.get_template('test_matrix.html').render({'suites': prov_suites[prov]})
    with open(os.path.join(log_path.strpath, '{}.html'.format(prov)), "w") as f:
        f.write(data)


try:
    shutil.copytree(template_path.join('dist').strpath, os.path.join(log_path.strpath, 'dist'))
except OSError:
    pass
