import pytest
from py.error import ENOENT
from selenium.common.exceptions import WebDriverException

import utils.browser
from utils.datafile import template_env
from utils.path import log_path
from fixtures import navigation

nav_fixture_names = filter(lambda x: x.endswith('_pg'), dir(navigation))
browser_fixtures = set(['browser'] + nav_fixture_names)

failed_test_tracking = {
    'tests': list(),
    'total_failed': 0,
    'total_errored': 0,
}


def pytest_runtest_setup(item):
    if set(getattr(item, 'fixturenames', [])) & browser_fixtures:
        utils.browser.ensure_browser_open()


def pytest_exception_interact(node, call, report):
    if set(getattr(node, 'fixturenames', [])) & browser_fixtures:
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
        }

        try:
            template_data['screenshot'] = utils.browser.browser().get_screenshot_as_base64()
        except (AttributeError, WebDriverException):
            # See comments utils.browser.ensure_browser_open for why these two exceptions
            template_data['screenshot'] = None
            template_data['screenshot_error'] = 'browser error'
        except Exception as ex:
            # If this fails for any other reason,
            # leave out the screenshot but record the reason
            template_data['screenshot'] = None
            if ex.message:
                screenshot_error = '%s: %s' % (type(ex).__name__, ex.message)
            else:
                screenshot_error = type(ex).__name__
            template_data['screenshot_error'] = screenshot_error

        failed_test_tracking['tests'].append(template_data)
        if is_error:
            failed_test_tracking['total_errored'] += 1
        else:
            failed_test_tracking['total_failed'] += 1


def pytest_sessionfinish(session, exitstatus):
    failed_tests_template = template_env.get_template('failed_browser_tests.html')
    outfile = log_path.join('failed_browser_tests.html')

    # Clean out any old reports
    try:
        outfile.remove(ignore_errors=True)
    except ENOENT:
        pass

    # Generate a new one if needed
    if failed_test_tracking['tests']:
        failed_tests_report = failed_tests_template.render(**failed_test_tracking)
        outfile.write(failed_tests_report)


@pytest.fixture(scope='session')
def browser():
    return utils.browser.browser
