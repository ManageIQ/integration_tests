# -*- coding: utf-8 -*-
# pylint: disable=broad-except

from __future__ import print_function

import datetime
import json
import re

import pytest
from polarion_docstrings import parser as docparser
from polarion_docstrings import polarion_fields

# pylint: disable=no-name-in-module
from cfme.utils.conf import testcases
from cfme.utils.pytest_shortcuts import extract_fixtures_values

DUPLICATES = "duplicates.log"
TESTCASES = "test_case_import.json"
TESTRESULTS = "test_run_import.json"

CONF = {
    "gh_owner": testcases.get("gh_owner", "ManageIQ"),
    "gh_repo": testcases.get("gh_repo", "integration_tests"),
}

WHITELIST = [
    r"cfme/tests/infrastructure/test_quota_tagging.py::test_.*\[.*rhe?v",
    r"test_tenant_quota.py",
]
COMPILED_WHITELIST = re.compile("(" + ")|(".join(WHITELIST) + ")")

BLACKLIST = [
    "cfme/tests/containers/",
    "cfme/tests/openstack/",
    "test_import_own_module",
    "hawkular",
    r"\[.*rhos",
    r"\[.*rhev",
    r"\[.*rhv",
]
COMPILED_BLACKLIST = re.compile("(" + ")|(".join(BLACKLIST) + ")")

DEFAULT_CUSTOM_FIELDS = {
    "caseautomation": "automated",
    "caseimportance": "high",
    "caselevel": "component",
    "caseposneg": "positive",
    "testtype": "functional",
}

CASELEVELS = {"0": "component", "1": "integration", "2": "system", "3": "acceptance"}


STEP_NUMBERING = re.compile(r"[0-9]+[.)]? ?")
TIMESTAMP = "{:%Y%m%d%H%M%S}".format(datetime.datetime.now())


def pytest_addoption(parser):
    """Adds command line options."""
    group = parser.getgroup(
        "Polarion importers: options related to creation of XML files for Polarion importers"
    )
    group.addoption(
        "--generate-jsons",
        action="store_true",
        default=False,
        help="generate the JSON files for import",
    )
    group.addoption(
        "--jsons-no-blacklist",
        action="store_true",
        default=False,
        help="don't filter testcases using the built-in blacklist",
    )


def get_unicode_str(obj):
    """Makes sure obj is a unicode string."""
    try:
        # Python 2.x
        if isinstance(obj, unicode):
            return obj
        if isinstance(obj, str):
            return obj.decode("utf-8", errors="ignore")
        return unicode(obj)
    except NameError:
        # Python 3.x
        if isinstance(obj, str):
            return obj
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="ignore")
        return str(obj)


def _get_docstring(item):
    try:
        docstring = get_unicode_str(item.function.func_doc)
    except Exception:
        docstring = ""
    return docstring


def _get_caselevel(item):
    try:
        tier = item.get_marker("tier").args[0]
        tier_id = CASELEVELS[str(tier)]
    except Exception:
        tier_id = CASELEVELS["0"]
    return tier_id


def _get_description(item, docstring, automation_script):
    try:
        description = docparser.strip_polarion_data(docstring)
    except ValueError as err:
        print("Cannot parse the description of {}: {}".format(item.location[2], err))
        description = ""

    if not item.get_marker("manual"):
        # Description with timestamp and link to test case source.
        # The timestamp will not be visible in Polarion, but will cause Polarion
        # to update the "Updated" field even when there's no other change.
        description = '{0}<br id="{1}"/><br/><a href="{2}">Test Source</a>'.format(
            description, TIMESTAMP, automation_script
        )

    return description


def _get_automation_script(item):
    if item.get_marker("manual"):
        return None

    # The master here should probably link the latest "commit" eventually
    automation_script = "http://github.com/{0}/{1}/blob/master/{2}#L{3}".format(
        CONF["gh_owner"], CONF["gh_repo"], item.location[0], item.function.func_code.co_firstlineno
    )

    return automation_script


def _get_steps_and_results(parsed_docstring):
    if not parsed_docstring.get("testSteps"):
        return None

    test_steps = []
    expected_results = []

    steps = parsed_docstring.get("testSteps")
    results = parsed_docstring.get("expectedResults")
    steps = [STEP_NUMBERING.sub("", s[2]) for s in steps]
    results = [STEP_NUMBERING.sub("", r[2]) for r in results]

    for index, step in enumerate(steps):
        test_steps.append(step)

        try:
            result = results[index]
        except IndexError:
            result = ""
        expected_results.append(result)

    return test_steps, expected_results


def _get_assignee(parsed_docstring):
    assignee = parsed_docstring.get("assignee")
    if assignee and assignee[2]:
        return assignee[2]
    return None


def _get_initial_estimate(parsed_docstring):
    initial_estimate = parsed_docstring.get("initialEstimate")
    if initial_estimate and initial_estimate[2]:
        return initial_estimate[2]
    return None


def _get_requirement_name(item):
    try:
        return item.get_marker("requirement").args[0]
    except Exception:
        return None


def get_testcase_data(test_name, tests, processed_tests, item):
    """Gets data for single testcase entry."""
    if test_name in processed_tests:
        return
    processed_tests.append(test_name)

    testcase_data = DEFAULT_CUSTOM_FIELDS.copy()

    docstring = _get_docstring(item)
    parsed_docstring = docparser.parse_docstring(docstring) or {}

    automation_script = _get_automation_script(item)
    if automation_script:
        testcase_data["automation_script"] = automation_script

    testcase_title = parsed_docstring.get("title")
    testcase_title = testcase_title[2] if testcase_title else test_name
    testcase_data["title"] = testcase_title

    test_steps = _get_steps_and_results(parsed_docstring)
    if test_steps:
        testcase_data["testSteps"], testcase_data["expectedResults"] = test_steps

    for field, value in parsed_docstring.items():
        if field in polarion_fields.CUSTOM_FIELDS:
            testcase_data[field] = value[2]

    testcase_data["id"] = testcase_title
    testcase_data["assignee-id"] = _get_assignee(parsed_docstring)
    testcase_data["caseautomation"] = "manualonly" if item.get_marker("manual") else "automated"
    testcase_data["caselevel"] = _get_caselevel(item)
    testcase_data["description"] = _get_description(item, docstring, automation_script)
    testcase_data["id"] = test_name
    testcase_data["initial-estimate"] = _get_initial_estimate(parsed_docstring)
    testcase_data["linked-items"] = _get_requirement_name(item)
    testcase_data["params"] = extract_fixtures_values(item).keys() or None

    tests.append(testcase_data)


def get_testresult_data(test_name, tests, processed_tests, item):
    """Gets data for single test result entry."""
    if test_name in processed_tests:
        return
    processed_tests.append(test_name)

    testresult_data = {"title": test_name, "verdict": "waiting"}

    try:
        params = item.callspec.params
        parameters = {p: _get_name(v) for p, v in params.items()}
    except Exception:
        parameters = {}

    if parameters:
        testresult_data["params"] = parameters

    tests.append(testresult_data)


def _get_name(obj):
    if hasattr(obj, "_param_name"):
        return getattr(obj, "_param_name")
    elif hasattr(obj, "name"):
        return obj.name
    return str(obj)


def gen_duplicates_log(items):
    """Generates log file containing non-unique test cases names."""
    test_param = re.compile(r"\[.*\]")
    names = {}
    duplicates = set()

    for item in items:
        name = test_param.sub("", item.location[2])
        path = item.location[0]

        name_record = names.get(name)
        if name_record:
            name_record.add(path)
        else:
            names[name] = {path}

    for name, paths in names.items():
        if len(paths) > 1:
            duplicates.add(name)

    with open(DUPLICATES, "w") as f:
        for test in sorted(duplicates):
            f.write("{}\n".format(test))


def write_json(data_list, out_file):
    """Outputs data as JSON."""
    data_dict = {"results": data_list}
    with open(out_file, "w") as out:
        json.dump(data_dict, out, indent=4)


@pytest.mark.trylast
def pytest_collection_modifyitems(config, items):
    """Generates the XML files using collected items."""
    if not (config.getoption("generate_jsons") and config.getoption("--collect-only")):
        return

    gen_duplicates_log(items)

    no_blacklist = config.getoption("jsons_no_blacklist")

    tc_processed = []
    testcases = []
    tr_processed = []
    testresults = []

    for item in items:
        if "cfme/tests" not in item.nodeid:
            continue
        if (
            not no_blacklist
            and COMPILED_BLACKLIST.search(item.nodeid)      # noqa: W503
            and not COMPILED_WHITELIST.search(item.nodeid)  # noqa: W503
        ):
            continue

        name = item.location[2]

        get_testcase_data(name, testcases, tc_processed, item)
        get_testresult_data(name, testresults, tr_processed, item)

    write_json(testcases, TESTCASES)
    write_json(testresults, TESTRESULTS)
