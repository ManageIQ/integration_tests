import collections

import pytest

from utils import log


#: A dict of tests, and their state at various test phases
test_tracking = collections.defaultdict(dict)


# Expose the cfme logger as a fixture for convenience
@pytest.fixture(scope='session')
def logger():
    return log.logger


@pytest.mark.hookwrapper
def pytest_runtest_setup(item):
    path, lineno, domaininfo = item.location
    logger().info(log.format_marker(_format_nodeid(item.nodeid), mark="-"),
        extra={'source_file': path, 'source_lineno': lineno})
    yield


def pytest_collection_modifyitems(session, config, items):
    logger().info(log.format_marker('Starting new test run', mark="="))
    expression = config.getvalue('keyword') or False
    expr_string = ', will filter with "{}"'.format(expression) if expression else ''
    logger().info('Collected {} items{}'.format(len(items), expr_string))


@pytest.mark.hookwrapper
def pytest_runtest_logreport(report):
    # e.g. test_tracking['test_name']['setup'] = 'passed'
    #      test_tracking['test_name']['call'] = 'skipped'
    #      test_tracking['test_name']['teardown'] = 'failed'
    yield
    test_tracking[_format_nodeid(report.nodeid, False)][report.when] = report.outcome
    if report.when == 'teardown':
        path, lineno, domaininfo = report.location
        test_status = _test_status(_format_nodeid(report.nodeid, False))
        if test_status == "failed":
            try:
                logger().info(
                    "Managed providers: {}".format(
                        ", ".join([
                            prov.key for prov in pytest.store.current_appliance.managed_providers]))
                )
            except KeyError as ex:
                if 'ext_management_systems' in ex.msg:
                    logger().warning("Unable to query ext_management_systems table; DB issue")
                else:
                    raise
        logger().info(log.format_marker('{} result: {}'.format(_format_nodeid(report.nodeid),
                test_status)),
            extra={'source_file': path, 'source_lineno': lineno})
    if report.outcome == "skipped":
        # Usualy longrepr's a tuple, other times it isn't... :(
        try:
            longrepr = report.longrepr[-1]
        except AttributeError:
            longrepr = str(report.longrepr)

        logger().info(log.format_marker(longrepr))


def pytest_exception_interact(node, call, report):
    # Despite the name, call.excinfo is a py.code.ExceptionInfo object. Its traceback property
    # is similarly a py.code.TracebackEntry. The following lines, including "entry.lineno+1" are
    # based on the code there, which does unintuitive things with a traceback's line number.
    # This is the same code that powers py.test's output, so we gain py.test's magical ability
    # to get useful AssertionError output by doing it this way, which makes the voodoo worth it.
    entry = call.excinfo.traceback.getcrashentry()
    logger().error(call.excinfo.getrepr(),
        extra={'source_file': entry.path, 'source_lineno': entry.lineno + 1})


def pytest_sessionfinish(session, exitstatus):
    c = collections.Counter()
    for test in test_tracking:
        c[_test_status(test)] += 1
    # Prepend a total to the summary list
    results = ['total: {}'.format(sum(c.values()))] + map(
        lambda n: '{}: {}'.format(n[0], n[1]), c.items())
    # Then join it with commas
    summary = ', '.join(results)
    logger().info(log.format_marker('Finished test run', mark='='))
    logger().info(log.format_marker(str(summary), mark='='))


def _test_status(test_name):
    test_phase = test_tracking[test_name]
    # Test failure in setup or teardown is an error, which pytest doesn't report internally
    if 'failed' in (test_phase.get('setup', 'failed'), test_phase.get('teardown', 'failed')):
        return 'error'
    # A test can also be skipped
    elif 'skipped' in test_phase.get('setup', 'skipped'):
        return 'skipped'
    # Otherwise, report the call phase outcome (passed, skipped, or failed)
    else:
        return test_phase['call']


def _format_nodeid(nodeid, strip_filename=True):
    # Remove test class instances and filenames, replace with a dot to impersonate a method call
    nodeid = nodeid.replace('::()::', '.')
    # Trim double-colons to single
    nodeid = nodeid.replace('::', ':')
    # Strip filename (everything before and including the first colon)
    if strip_filename:
        try:
            return nodeid.split(':', 1)[1]
        except IndexError:
            # No colon to split on, return the whole nodeid
            return nodeid
    else:
        return nodeid
