import atexit

import pytest
from py.error import ENOENT
from jinja2 import Template

import utils.browser
from utils.path import data_path, log_path
from fixtures import navigation
#from utils.path import log_path

nav_fixture_names = filter(lambda x: x.endswith('_pg'), dir(navigation))
browser_fixtures = set(['browser'] + nav_fixture_names)

failed_test_tracking = {
    'tests': list(),
    'total_failed': 0,
    'total_errored': 0,
}


def pytest_runtest_setup(item):
    if set(item.fixturenames) & browser_fixtures:
        utils.browser.ensure_browser_open()


def pytest_exception_interact(node, call, report):
    if set(node.fixturenames) & browser_fixtures:
        short_tb = '%s\n%s' % (call.excinfo.type.__name__, call.excinfo.value)
        # base64 encoded to go into a data uri, same for screenshots
        full_tb = str(report.longrepr).encode('base64').strip()
        # errors are when exceptions are thrown outside of the test call phase
        is_error = report.when != 'call'

        template_data = {
            'name': node.name,
            'file': node.fspath,
            'is_error': is_error,
            'fail_stage': report.when,
            'short_tb': short_tb,
            'full_tb': full_tb,
            'screenshot': utils.browser.browser().get_screenshot_as_base64()
        }
        failed_test_tracking['tests'].append(template_data)
        if is_error:
            failed_test_tracking['total_errored'] += 1
        else:
            failed_test_tracking['total_failed'] += 1


def pytest_sessionfinish(session, exitstatus):
    failed_tests_template = data_path.join('templates', 'failed_browser_tests.html').read()
    outfile = log_path.join('failed_browser_tests.html')

    # Clean out any old reports
    try:
        outfile.remove(ignore_errors=True)
    except ENOENT:
        pass

    # Generate a new one if needed
    if failed_test_tracking['tests']:
        failed_tests_report = Template(failed_tests_template).render(**failed_test_tracking)
        outfile.write(failed_tests_report)


@pytest.fixture(scope='session')
def browser():
    return utils.browser.browser


def close_browser_no_matter_what():
    try:
        utils.browser.browser().quit()
    except:
        pass
atexit.register(close_browser_no_matter_what)
