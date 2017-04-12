import os
import contextlib

import fixtures
from fixtures.soft_assert import soft_assert, SoftAssertionError


@contextlib.contextmanager
def use_soft_assert():
    assertion_record = []
    gen = soft_assert(request=None)
    try:
        yield next(gen), assertion_record
    except SoftAssertionError as e:
        assertion_record.extend(e.failed_assertions)
    except StopIteration:
        pass


pytest_plugins = 'pytester'
# Tests in this module are a little bit weird, since soft_assert hooks in to pytest's call phase.
# The only way to actually test the call phase hook is to run pytest inside pytest using
# the pytester plugin.

test_file = """
import imp

soft_assert_path = '{}'
imp.load_source('soft_assert', soft_assert_path)
pytest_plugins = 'soft_assert'


def test_soft_assert(soft_assert):
    soft_assert(None)
    soft_assert(False, 'soft_assert message!')
""".format(os.path.abspath(fixtures.soft_assert.__file__.replace('pyc', 'py')))

test_output_match_lines = [
    ">           raise SoftAssertionError(_thread_locals.caught_asserts)",
    "E           SoftAssertionError: ",
    "E           soft_assert(None) ({testfile}:9)",
    "E           soft_assert message! ({testfile}:10)",
]


def test_soft_assert_call_hook(testdir):
    # create and run the pytest
    pyfile = testdir.makepyfile(test_file)
    result = testdir.runpytest()
    # replace the testfile name in the expected output names,
    # then check filename and lineno are correct in the failure output
    result.stdout.fnmatch_lines([s.format(testfile=pyfile) for s in test_output_match_lines])


def test_soft_assert_cm():
    with use_soft_assert() as (soft_assert, assertion_record):
        soft_assert(None)
        soft_assert(False, 'Value is False')
        soft_assert(True, 'Value is True')


    # the number of failed assertions is what we expect
    assert len(assertion_record) == 2

    # showing code context instead of the message where appropriate
    assert 'soft_assert(None)' in assertion_record

    # showing the message when it's passed in
    assert 'Value is False' in assertion_record

    # assertions that pass aren't reported
    assert 'Value is True' not in assertion_record

    # assertions are cleared if soft_assert is used twice in a test
    with use_soft_assert() as (soft_assert, assertion_record):
        # if assertions aren't cleared, this will erroneously raise AssertionError
        pass
    assert not assertion_record
