import pytest

from collections import defaultdict
from lxml import etree
import re
from utils.conf import xunit
from utils.pytest_shortcuts import extract_fixtures_values


default_custom_fields = {
    "caseautomation": "automated",
    "caseimportance": "high",
    "caselevel": "component",
    "caseposneg": "positive",
    "testtype": "functional",
    "subtype1": "-",
    "subtype2": "-"
}


def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme')
    parser.addoption("--generate-xmls", action="store_true", default=False,
        help="generate the xml files for import")
    parser.addoption("--generate-legacy-xmls", action="store_true", default=False,
        help="generate the legacy xml files for import")
    parser.addoption("--xmls-testrun-id",
        help="testrun id")
    parser.addoption("--xmls-testrun-title",
        help="testrun title")


def testcase_gen(
        test_name, description=None, parameters=None, custom_fields=None, linked_items=None):
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
    for tc_id, content in custom_fields.iteritems():
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


def testresult_gen(test_name, parameters=None, result=None):
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
    for param, value in parameters.iteritems():
        param_el = etree.Element(
            'property', name="polarion-parameter-{}".format(param), value=value)
        properties.append(param_el)
    testcase.append(properties)
    return testcase


def testrun_gen(tests, filename, config, collectonly=True):
    prop_dict = {
        'testrun-template-id': xunit.get('testrun_template_id'),
        'testrun-title': config.getoption('xmls_testrun_title') or xunit.get('testrun_title'),
        'testrun-id': config.getoption('xmls_testrun_id') or xunit.get('testrun_id'),
        'project-id': xunit['project_id'],
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
    for prop_name, prop_value in prop_dict.iteritems():
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
            testsuite.append(testresult_gen(data['name'], data.get('params')))
            results_count['skipped'] += 1
        else:
            testsuite.append(testresult_gen(
                data['name'], data.get('params'), result=data.get('result')))
            results_count[data['result']] += 1
    testsuite.attrib['tests'] = str(no_tests)
    testsuite.attrib['failures'] = str(results_count['failure'])
    testsuite.attrib['skipped'] = str(results_count['skipped'])
    testsuite.attrib['errors'] = str(results_count['error'])
    testsuite.attrib['name'] = "cfme-tests"
    xml = etree.ElementTree(testsuites)
    xml.write(filename, pretty_print=True)


def get_name(obj):
    if hasattr(obj, '_param_name'):
        return getattr(obj, '_param_name')
    elif hasattr(obj, 'name'):
        return obj.name
    else:
        return str(obj)


caselevels = {
    '0': 'component',
    '1': 'integration',
    '2': 'system',
    '3': 'acceptance'
}


@pytest.mark.trylast
def pytest_collection_modifyitems(session, config, items):
    if not config.getoption('generate_xmls') and not config.getoption('generate_legacy_xmls'):
        return
    # all "legacy" conditions can be removed once parametrization is finished
    legacy = True if config.getoption('generate_legacy_xmls') else False
    a = defaultdict(dict)
    ntr = []
    for item in items:
        a[item.location[0]][re.sub('\[.*\]', '', item.location[2])] = a[item.location[0]].get(
            re.sub('\[.*\]', '', item.location[2]), 0) + 1
    with open('duplicates.log', 'w') as f:
        for module, tests in a.iteritems():
            for test in tests:
                if test not in ntr:
                    ntr.append(test)
                else:
                    f.write("{}\n".format(test))

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

    test_name = []
    for item in items:
        work_items = []
        custom_fields = {}
        try:
            description = item.function.func_doc
        except:
            description = ""
        try:
            requirement = item.get_marker('requirement').args[0]
            from utils.conf import cfme_data
            requirement_id = cfme_data['requirements'][requirement]
            work_items.append({'id': requirement_id, 'role': 'verifies'})
        except:
            pass
        try:
            tier = item.get_marker('tier').args[0]
            tier_id = caselevels[str(tier)]
            custom_fields['caselevel'] = tier_id
        except:
            pass

        param_list = extract_fixtures_values(item).keys() if not legacy else None

        manual = item.get_marker('manual')
        if not manual:
            # The master here should probably link the latest "commit" eventually
            automation_script = 'http://github.com/{}/{}/blob/master/{}#L{}'.format(
                xunit['gh_owner'],
                xunit['gh_repo'],
                item.location[0],
                item.function.func_code.co_firstlineno
            )
            custom_fields['caseautomation'] = "automated"
            custom_fields['automation_script'] = automation_script
            description = '{}<br/><br/><a href="{}">Test Source</a>'.format(
                description, automation_script)
        else:
            custom_fields['caseautomation'] = "manualonly"
            description = '{}'.format(description)

        name = re.sub('\[.*\]', '', item.name) if not legacy else item.name
        if name not in test_name:
            test_name.append(name)
            testcases.append(
                testcase_gen(
                    name,
                    description=description,
                    parameters=param_list,
                    linked_items=work_items,
                    custom_fields=custom_fields))

    xml = etree.ElementTree(testcases)
    xml.write('test_case_import.xml', pretty_print=True)

    test_name = []
    tests = []
    for item in items:
        if legacy:
            if item.name in test_name:
                continue
            name = item.name
            param_dict = None
            test_name.append(name)
        else:
            name = re.sub(r'\[.*\]', '', item.name)
            try:
                params = item.callspec.params
                param_dict = {p: get_name(v) for p, v in params.iteritems()}
            except Exception:
                param_dict = {}
        tests.append({'name': name, 'params': param_dict, 'result': None})
    testrun_gen(tests, 'test_run_import.xml', config, collectonly=True)
