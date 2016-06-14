"""requires_test(test_name_or_nodeid): Mark a test as requiring another test

If another test is required to have run and passed before a suite of tests has
any hope of succeeding, such as a smoke test, apply this mark to those tests.

It takes a test name as the only positional argument. In the event that the
test name is ambiguous, a full py.test nodeid can be used. A test's nodeid can
be found by inspecting the request.node.nodeid attribute inside the required
test item.

"""

import pytest

_no_mark_arg_err = '{} mark required test name or nodeid as first argument'


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


def _find_test_in_reports(test_id, reports):
    # nodeids end with the test name, so the description of this mark
    # oversimplifies things a little bit. The actual check for a test
    # match is that any preceding test nodeid ends with the arg passed
    # to the mark, so we can easily match the test name, test nodeid, and
    # anything in between.

    return any([report.nodeid.endswith(test_id) for report in reports])


def pytest_runtest_setup(item):
    mark = 'requires_test'
    if mark not in item.keywords:
        # mark wasn't invoked, short out
        return
    else:
        try:
            test_id = item.keywords[mark].args[0]
        except IndexError:
            # mark called incorrectly, explode
            raise Exception(_no_mark_arg_err.format(mark))

    reporter = item.config.pluginmanager.getplugin('terminalreporter')
    passed = reporter.stats.get('passed', [])
    failed = reporter.stats.get('failed', [])
    skipped = reporter.stats.get('skipped', [])

    if _find_test_in_reports(test_id, passed):
        # Required test passed, short out
        return

    if _find_test_in_reports(test_id, failed):
        error_verb = 'failed'
    elif _find_test_in_reports(test_id, skipped):
        error_verb = 'was skipped'
    else:
        error_verb = 'not yet run or does not exist'

    errmsg = 'required test {} {}'.format(test_id, error_verb)
    pytest.skip(errmsg)
