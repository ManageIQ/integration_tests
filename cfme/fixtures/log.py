import collections

import attr
import pytest

from cfme.fixtures.pytest_store import store
from cfme.utils import log
from cfme.utils.appliance import find_appliance

#: A dict of tests, and their state at various test phases
test_tracking = collections.defaultdict(dict)


# Expose the cfme logger as a fixture for convenience
@pytest.fixture(scope='session')
def logger():
    return log.logger


def pytest_configure(config):
    config.pluginmanager.register(LogExtraData(config))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    path, lineno, domaininfo = item.location
    log.logger.info(log.format_marker(_format_nodeid(item.nodeid), mark="-"),
        extra={'source_file': path, 'source_lineno': lineno})
    yield


def pytest_collection_modifyitems(session, config, items):
    log.logger.info(log.format_marker('Starting new test run', mark="="))
    expression = config.getvalue('keyword') or False
    expr_string = f', will filter with "{expression}"' if expression else ''
    log.logger.info('Collected {} items{}'.format(len(items), expr_string))


@attr.s(frozen=True)
class LogExtraData:
    config = attr.ib()

    @property
    def managed_known_providers(self):
        appliance = find_appliance(self.config)
        return [prov.key for prov in appliance.managed_known_providers]

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_logreport(self, report):
        # e.g. test_tracking['test_name']['setup'] = 'passed'
        #      test_tracking['test_name']['call'] = 'skipped'
        #      test_tracking['test_name']['teardown'] = 'failed'
        yield
        test_tracking[_format_nodeid(report.nodeid, False)][report.when] = report.outcome
        if report.when == 'teardown' and store.parallel_session is None:
            path, lineno, domaininfo = report.location
            test_status = _test_status(_format_nodeid(report.nodeid, False))
            if test_status == "failed":
                try:
                    log.logger.info(
                        "Managed providers: {}".format(
                            ", ".join(self.managed_known_providers))
                    )
                except KeyError as ex:
                    if 'ext_management_systems' in ex.msg:
                        log.logger.warning("Unable to query ext_management_systems table; DB issue")
                    else:
                        raise
            log.logger.info(log.format_marker('{} result: {}'.format(_format_nodeid(report.nodeid),
                    test_status)),
                extra={'source_file': path, 'source_lineno': lineno})
        if report.outcome == "skipped":
            log.logger.info(log.format_marker(report.longreprtext))


def pytest_exception_interact(node, call, report):
    # Despite the name, call.excinfo is a py.code.ExceptionInfo object. Its traceback property
    # is similarly a py.code.TracebackEntry. The following lines, including "entry.lineno+1" are
    # based on the code there, which does unintuitive things with a traceback's line number.
    # This is the same code that powers py.test's output, so we gain py.test's magical ability
    # to get useful AssertionError output by doing it this way, which makes the voodoo worth it.
    entry = call.excinfo.traceback.getcrashentry()
    log.logger.error(call.excinfo.getrepr(),
        extra={'source_file': entry.path, 'source_lineno': entry.lineno + 1})


def pytest_sessionfinish(session, exitstatus):
    c = collections.Counter()
    for test in test_tracking:
        c[_test_status(test)] += 1
    # Prepend a total to the summary list
    results = ['total: {}'.format(sum(c.values()))] + [
        f'{k}: {v}' for k, v in c.items()]
    # Then join it with commas
    summary = ', '.join(results)
    log.logger.info(log.format_marker('Finished test run', mark='='))
    log.logger.info(log.format_marker(str(summary), mark='='))


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
        return test_phase.get('call', 'skipped')


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
