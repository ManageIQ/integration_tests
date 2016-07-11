"""smoke: Mark a test as a smoke test to be run as early as possible

Mark a single test as a smoke test, moving it to the beginning of a test run.

The --halt-on-smoke-test-failure command-line argument will halt after running the smoke tests
if any smoke tests fail.

This mark must be used with caution, as marked tests must be able to run out of order,
and in isolation.

Furthermore, smoke tests are an excellent target for the requires_test mark
since they're run first.

"""
from collections import defaultdict
from time import time

import pytest

from fixtures.terminalreporter import reporter


def pytest_addoption(parser):
    group = parser.getgroup("smoke_tests", "smoke test marking")
    group._addoption('--halt-on-smoke-test-failure',
           action="store_true", dest="haltonsmokefail", default=False,
           help="halt the test run if smoke tests fail")


def pytest_configure(config):
    smoke_tests = SmokeTests(reporter(config))
    config.pluginmanager.register(smoke_tests, 'smoke_tests')
    config.addinivalue_line('markers', __doc__.splitlines()[0])


@pytest.mark.trylast
def pytest_collection_modifyitems(session, config, items):
    # XXX: This also handles moving long_running tests to the front of the test module
    # There are a few different ways to handle this batter, but rather than building in logic
    # for both smoke and long_running marks to make sure each one reorders tests with respect to
    # the other, it made sense to just combine this here for now and organize these marks better
    # later on.

    # Split marked and unmarked tests
    split_tests = defaultdict(list)
    for item in items:
        for mark in ('smoke', 'long_running'):
            if mark in item.keywords:
                key = mark
                break
        else:
            key = None

        split_tests[key].append(item)

    # Now rebuild the items list with the smoke tests first, followed by long_running
    # with unmarked tests at the end
    session.items = split_tests['smoke'] + split_tests['long_running'] + split_tests[None]

    if split_tests['smoke']:
        # If there are smoke tests, use the fancy smoke test reporter
        smoke_tests = config.pluginmanager.getplugin('smoke_tests')
        reporter(config).write_sep('=', 'Running smoke tests')
        smoke_tests.start_time = time()
        smoke_tests.halt_on_fail = config.getvalue('haltonsmokefail')


class SmokeTests(object):
    # state trackers
    run_tests = 0
    failed_tests = 0
    complete = False
    reported = False
    start_time = 0.0
    halt_on_fail = False

    def __init__(self, reporter):
        self.reporter = reporter

    def pytest_runtest_logreport(self, report):
        if 'smoke' in report.keywords and report.when == 'teardown':
            self.run_tests += 1

        if report.outcome == 'failed':
            self.failed_tests += 1

        if self.complete and not self.reported:
            time_taken = time() - self.start_time
            self.reported = True

            if self.failed_tests:
                if self.halt_on_fail:
                    pytest.exit('%d smoke tests failed, test run halted' % self.failed_tests)
                else:
                    report = ('%d of %d smoke tests failed in %.2f seconds'
                        % (self.failed_tests, self.run_tests, time_taken))
                    self.reporter.write_sep('-', report, red=True)
            else:
                report = '%d smoke tests passed in %.2f seconds' % (self.run_tests, time_taken)
                self.reporter.write_sep('-', report, green=True)

    def pytest_runtest_teardown(self, item, nextitem):
        # This condition should only be met on the last smoke test, since they were
        # all moved to the top of the test run.
        if item.get_marker('smoke') and not (nextitem and nextitem.get_marker('smoke')):
            self.complete = True
