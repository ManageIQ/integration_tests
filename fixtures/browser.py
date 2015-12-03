import pytest
from py.error import ENOENT

import utils.browser
from cfme.fixtures.pytest_selenium import take_screenshot
from fixtures.artifactor_plugin import art_client, get_test_idents
from utils.datafile import template_env
from utils.path import log_path

browser_fixtures = {'browser'}

failed_test_tracking = {
    'tests': list(),
    'total_failed': 0,
    'total_errored': 0,
}


def pytest_namespace():
    # Return the contents of this file as the 'sel' namespace in pytest.
    from cfme.fixtures import pytest_selenium
    return {'sel': pytest_selenium}


def pytest_runtest_setup(item):
    if set(getattr(item, 'fixturenames', [])) & browser_fixtures:
        utils.browser.ensure_browser_open()


def pytest_exception_interact(node, call, report):
    name, location = get_test_idents(node)
    val = call.excinfo.value.message.decode('utf-8', 'ignore')
    short_tb = '%s\n%s' % (call.excinfo.type.__name__, val.encode('ascii', 'xmlcharrefreplace'))
    art_client.fire_hook('filedump', test_location=location, test_name=name,
                  filename="traceback.txt", contents=str(report.longrepr), fd_ident="tb")
    art_client.fire_hook('filedump', test_location=location, test_name=name,
                  filename="short-traceback.txt", contents=short_tb, fd_ident="short_tb")

    # base64 encoded to go into a data uri, same for screenshots
    full_tb = str(report.longrepr).encode('base64').strip()
    # errors are when exceptions are thrown outside of the test call phase
    report.when = getattr(report, 'when', 'setup')
    is_error = report.when != 'call'

    template_data = {
        'name': node.name,
        'file': node.fspath,
        'is_error': is_error,
        'fail_stage': report.when,
        'short_tb': short_tb,
        'full_tb': full_tb,
    }

    # Before trying to take a screenshot, we used to check if one of the browser_fixtures was
    # in this node's fixturenames, but that was too limited and preventing the capture of
    # screenshots. If removing that conditional now makes this too broad, we should consider
    # an isinstance(val, WebDriverException) check in addition to the browser fixture check that
    # exists here in commit 825ef50fd84a060b58d7e4dc316303a8b61b35d2

    screenshot = take_screenshot()
    template_data['screenshot'] = screenshot.png
    template_data['screenshot_error'] = screenshot.error
    if screenshot.png:
        art_client.fire_hook('filedump', test_location=location, test_name=name,
            filename="screenshot.png", fd_ident="screenshot", mode="wb", contents_base64=True,
            contents=template_data['screenshot'])
    if screenshot.error:
        art_client.fire_hook('filedump', test_location=location, test_name=name,
            filename="screenshot.txt", fd_ident="screenshot", mode="w", contents_base64=False,
            contents=template_data['screenshot_error'])

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
