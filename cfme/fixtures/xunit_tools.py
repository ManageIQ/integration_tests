# pylint: disable=broad-except
import datetime
import re

import pytest
from lxml import etree

from cfme.utils.conf import cfme_data
from cfme.utils.conf import xunit
from cfme.utils.pytest_shortcuts import extract_fixtures_values
# pylint: disable=no-name-in-module


whitelist = [
    r'cfme/tests/infrastructure/test_quota_tagging.py::test_.*\[.*rhe?v',
    r'test_tenant_quota.py',
    r'cfme/tests/v2v/.*',
]
compiled_whitelist = re.compile('(' + ')|('.join(whitelist) + ')')


blacklist = [
    'cfme/tests/openstack/',
    'hawkular',
    r'\[.*rhos',
    r'\[.*rhev',
    r'\[.*rhv',
]
compiled_blacklist = re.compile('(' + ')|('.join(blacklist) + ')')


timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())


default_custom_fields = {
    "caseautomation": "automated",
    "caseimportance": "high",
    "caselevel": "component",
    "caseposneg": "positive",
    "testtype": "functional",
    "subtype1": "-",
    "subtype2": "-"
}


caselevels = {
    '0': 'component',
    '1': 'integration',
    '2': 'system',
    '3': 'acceptance'
}


test_param = re.compile(r'\[.*\]')


def pytest_addoption(parser):
    """Adds command line options."""
    group = parser.getgroup(
        "Polarion importers: options related to creation of XML files for Polarion importers")
    group.addoption("--generate-xmls", action="store_true", default=False,
        help="generate the xml files for import")
    group.addoption("--generate-legacy-xmls", action="store_true", default=False,
        help="generate the legacy xml files for import")
    group.addoption("--xmls-testrun-id",
        help="testrun id")
    group.addoption("--xmls-testrun-title",
        help="testrun title")
    group.addoption("--xmls-no-blacklist", action="store_true", default=False,
        help="don't filter testcases using the built-in blacklist")


def get_polarion_name(item):
    """Gets Polarion test case name out of the Node ID."""
    param_strip = test_param.sub('', item.location[2])
    return (item.location[2], param_strip)


def testcase_record(
        test_name, description=None, parameters=None, custom_fields=None, linked_items=None):
    """Generates single testcase entry."""
    linked_items = linked_items or []
    custom_fields_update = custom_fields or {}
    custom_fields = default_custom_fields.copy()
    custom_fields.update(custom_fields_update)
    parameters = parameters or []
    testcase = etree.Element('testcase', id=test_name)
    title = etree.Element('title')
    title.text = test_name
    description_el = etree.Element('description')
    description_el.text = description or ""
    testcase.append(title)
    testcase.append(description_el)
    test_steps = etree.Element('test-steps')
    test_step = etree.Element('test-step')
    test_step_col = etree.Element('test-step-column', id="step")
    for param in parameters:
        param_el = etree.Element('parameter', name=param, scope="local")
        test_step_col.append(param_el)
    test_step.append(test_step_col)
    test_steps.append(test_step)
    testcase.append(test_steps)
    custom_fields_el = etree.Element('custom-fields')
    for tc_id, content in custom_fields.items():
        custom_field = etree.Element('custom-field', id=tc_id, content=content)
        custom_fields_el.append(custom_field)
    testcase.append(custom_fields_el)
    if linked_items:
        work_items = etree.Element('linked-work-items')
        for work_item in linked_items:
            work_item_el = etree.Element('linked-work-item')
            work_item_el.attrib['workitem-id'] = work_item['id']
            work_item_el.attrib['role-id'] = work_item['role']
            work_items.append(work_item_el)
        testcase.append(work_items)
    return testcase


def get_testcase_data(name, tests, processed_test, item, legacy=False):
    """Gets data for single testcase entry."""
    if name in processed_test:
        return

    work_items = []
    custom_fields = {}
    try:
        description = item.function.__doc__
    except Exception:
        description = ""
    try:
        requirement = item.get_closest_marker('requirement').args[0]
        requirement_id = cfme_data['requirements'][requirement]
        work_items.append({'id': requirement_id, 'role': 'verifies'})
    except Exception:
        pass
    try:
        tier = item.get_closest_marker('tier').args[0]
        tier_id = caselevels[str(tier)]
        custom_fields['caselevel'] = tier_id
    except Exception:
        pass

    param_list = list(extract_fixtures_values(item).keys()) if not legacy else None

    manual = item.get_closest_marker('manual')
    if not manual:
        # The master here should probably link the latest "commit" eventually
        automation_script = 'http://github.com/{0}/{1}/blob/master/{2}#L{3}'.format(
            xunit['gh_owner'],
            xunit['gh_repo'],
            item.location[0],
            item.function.__code__.co_firstlineno
        )
        custom_fields['caseautomation'] = "automated"
        custom_fields['automation_script'] = automation_script
        # Description with timestamp and link to test case source.
        # The timestamp will not be visible in Polarion, but will cause Polarion
        # to update the "Updated" field even when there's no other change.
        description = '{0}<br id="{1}"/><br/><a href="{2}">Test Source</a>'.format(
            description, timestamp, automation_script)
    else:
        custom_fields['caseautomation'] = "manualonly"
        description = '{}'.format(description)

    processed_test.append(name)
    tests.append(dict(
        test_name=name,
        description=description,
        parameters=param_list,
        linked_items=work_items,
        custom_fields=custom_fields))


def testresult_record(test_name, parameters=None, result=None):
    """Generates single test result entry."""
    testcase = etree.Element('testcase', name=test_name)
    parameters = parameters or {}
    extra = None
    if result == "skipped" or not result:
        extra = etree.Element('skipped', message='Skipped', type='skipped')
        testcase.append(extra)
    elif result == "error":
        extra = etree.Element('error', message="Error", type='error')
        testcase.append(extra)
    elif result == "failed":
        extra = etree.Element('failure', message="Failed", type='failure')
        testcase.append(extra)
    properties = etree.Element('properties')
    testcase_id = etree.Element('property', name="polarion-testcase-id", value=test_name)
    properties.append(testcase_id)
    for param, value in parameters.items():
        param_el = etree.Element(
            'property', name="polarion-parameter-{}".format(param), value=value)
        properties.append(param_el)
    testcase.append(properties)
    return testcase


def get_testresult_data(name, tests, processed_test, item, legacy=False):
    """Gets data for single test result entry."""
    if legacy:
        if name in processed_test:
            return
        param_dict = None
        processed_test.append(name)
    else:
        try:
            params = item.callspec.params
            param_dict = {p: _get_name(v) for p, v in params.items()}
        except Exception:
            param_dict = {}
    tests.append({'name': name, 'params': param_dict, 'result': None})


def testrun_gen(tests, filename, config, collectonly=True):
    """Generates content of the XML file used for test run import."""
    prop_dict = {
        'testrun-template-id': xunit.get('testrun_template_id'),
        'testrun-title': config.getoption('xmls_testrun_title') or xunit.get('testrun_title'),
        'testrun-id': config.getoption('xmls_testrun_id') or xunit.get('testrun_id'),
        'project-id': xunit['project_id'],
        'group-id': xunit.get('group_id'),
        'dry-run': xunit.get('dry_run', False),
        'testrun-status-id': xunit['testrun_status_id'],
        'lookup-method': xunit['lookup_method']
    }

    testsuites = etree.Element("testsuites")
    testsuite = etree.Element("testsuite")
    properties = etree.Element("properties")
    property_resp = etree.Element(
        'property', name='polarion-response-{}'.format(
            xunit['response']['id']), value=xunit['response']['value'])
    properties.append(property_resp)
    for prop_name, prop_value in prop_dict.items():
        if prop_value is None:
            continue
        prop_el = etree.Element(
            'property', name="polarion-{}".format(prop_name), value=str(prop_value))
        properties.append(prop_el)
    testsuites.append(properties)
    testsuites.append(testsuite)

    no_tests = 0
    results_count = {
        'passed': 0,
        'skipped': 0,
        'failure': 0,
        'error': 0
    }
    for data in tests:
        no_tests += 1
        if collectonly:
            testsuite.append(testresult_record(data['name'], data.get('params')))
            results_count['skipped'] += 1
        else:
            testsuite.append(testresult_record(
                data['name'], data.get('params'), result=data.get('result')))
            results_count[data['result']] += 1
    testsuite.attrib['tests'] = str(no_tests)
    testsuite.attrib['failures'] = str(results_count['failure'])
    testsuite.attrib['skipped'] = str(results_count['skipped'])
    testsuite.attrib['errors'] = str(results_count['error'])
    testsuite.attrib['name'] = "cfme-tests"
    xml = etree.ElementTree(testsuites)
    xml.write(filename, pretty_print=True)


def testcases_gen(tests, filename):
    """Generates content of the XML file used for test cases import."""
    testcases = etree.Element("testcases")
    testcases.attrib['project-id'] = xunit['project_id']
    response_properties = etree.Element("response-properties")
    response_property = etree.Element(
        "response-property", name=xunit['response']['id'], value=xunit['response']['value'])
    response_properties.append(response_property)
    properties = etree.Element("properties")
    lookup = etree.Element("property", name="lookup-method", value="custom")
    properties.append(lookup)
    dry_run = etree.Element("property", name="dry-run", value=str(xunit.get("dry_run", "false")))
    properties.append(dry_run)
    testcases.append(response_properties)
    testcases.append(properties)

    for data in tests:
        testcases.append(testcase_record(**data))
    xml = etree.ElementTree(testcases)
    xml.write(filename, pretty_print=True)


def _get_name(obj):
    if hasattr(obj, '_param_name'):
        return getattr(obj, '_param_name')
    elif hasattr(obj, 'name'):
        return obj.name
    return str(obj)


def gen_duplicates_log(items):
    """Generates log file containing non-unique test cases names."""
    names = {}
    duplicates = set()

    for item in items:
        name = test_param.sub('', item.location[2])
        path = item.location[0]

        name_record = names.get(name)
        if name_record:
            name_record.add(path)
        else:
            names[name] = {path}

    [duplicates.add(name) for name, paths in names.items() if len(paths) > 1]

    with open('duplicates.log', 'w') as f:
        for test in sorted(duplicates):
            f.write('{}\n'.format(test))


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    """Generates the XML files using collected items."""
    if not (config.getoption('generate_xmls') or config.getoption('generate_legacy_xmls')):
        return

    gen_duplicates_log(items)

    no_blacklist = config.getoption('xmls_no_blacklist')
    collectonly = config.getoption('--collect-only')
    # all "legacy" conditions can be removed once parametrization is finished
    legacy = config.getoption('generate_legacy_xmls')

    tc_processed = []
    tc_data = []
    tr_processed = []
    tr_data = []

    for item in items:
        if 'cfme/tests' not in item.nodeid:
            continue
        if (not no_blacklist and
                compiled_blacklist.search(item.nodeid) and
                not compiled_whitelist.search(item.nodeid)):
            continue

        legacy_name, parametrized_name = get_polarion_name(item)
        name = legacy_name if legacy else parametrized_name

        get_testcase_data(name, tc_data, tc_processed, item, legacy)
        get_testresult_data(name, tr_data, tr_processed, item, legacy)

    testcases_gen(tc_data, 'test_case_import.xml')
    testrun_gen(tr_data, 'test_run_import.xml', config, collectonly=collectonly)
