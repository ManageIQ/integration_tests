import base64
from urllib.error import URLError

from py.error import ENOENT

from cfme.fixtures.artifactor_plugin import fire_art_test_hook
from cfme.utils import browser as browser_util
from cfme.utils import safe_string
from cfme.utils.appliance import find_appliance
from cfme.utils.datafile import template_env
from cfme.utils.log import logger
from cfme.utils.path import log_path
from cfme.utils.path import project_path
browser_fixtures = {'browser'}

failed_test_tracking = {
    'tests': list(),
    'total_failed': 0,
    'total_errored': 0,
}


def pytest_runtest_setup(item):
    from cfme.utils.appliance import (
        DummyAppliance,
    )

    appliance = find_appliance(item, require=False)
    if isinstance(appliance, DummyAppliance):
        return

    if set(getattr(item, 'fixturenames', [])) & browser_fixtures:
        browser_util.manager.start()


def pytest_exception_interact(node, call, report):
    from cfme.fixtures.pytest_store import store
    from http.client import BadStatusLine
    from socket import error
    val = safe_string(call.excinfo.value)
    if isinstance(call.excinfo.value, (URLError, BadStatusLine, error)):
        logger.error("internal Exception:\n %s", str(call.excinfo))
        browser_util.manager.start()  # start will quit first and cycle wharf as well

    last_lines = "\n".join(report.longreprtext.split("\n")[-4:])

    ascii_val = val.encode('ascii', 'xmlcharrefreplace').decode('ascii')
    short_tb = f'{last_lines}\n{call.excinfo.type.__name__}\n{ascii_val}'
    fire_art_test_hook(
        node, 'filedump',
        description="Traceback", contents=report.longreprtext, file_type="traceback",
        display_type="danger", display_glyph="align-justify", group_id="pytest-exception",
        slaveid=store.slaveid)
    fire_art_test_hook(
        node, 'filedump',
        description="Short traceback", contents=short_tb, file_type="short_tb",
        display_type="danger", display_glyph="align-justify", group_id="pytest-exception",
        slaveid=store.slaveid)
    exception_name = call.excinfo.type.__name__
    exception_lineno = call.excinfo.traceback[-1].lineno
    exception_filename = str(call.excinfo.traceback[-1].path).replace(
        project_path.strpath + "/", ''
    )
    exception_location = f"{exception_filename}:{exception_lineno}"
    fire_art_test_hook(
        node, 'tb_info',
        exception=exception_name, file_line=exception_location,
        short_tb=short_tb, slave_id=store.slaveid
    )

    # base64 encoded to go into a data uri, same for screenshots
    tb = report.longreprtext
    if not isinstance(tb, bytes):
        tb = tb.encode('utf-8')
    full_tb = base64.b64encode(tb)
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

    screenshot = browser_util.take_screenshot()
    template_data['screenshot'] = screenshot.png
    template_data['screenshot_error'] = screenshot.error
    if screenshot.png:
        fire_art_test_hook(
            node, 'filedump',
            description="Exception screenshot", file_type="screenshot", mode="wb",
            contents_base64=True, contents=template_data['screenshot'], display_glyph="camera",
            group_id="pytest-exception", slaveid=store.slaveid)
    if screenshot.error:
        fire_art_test_hook(
            node, 'filedump',
            description="Screenshot error", mode="w", contents_base64=False,
            contents=template_data['screenshot_error'], display_type="danger",
            group_id="pytest-exception", slaveid=store.slaveid)

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
