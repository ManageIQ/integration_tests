import pytest

from cfme.fixtures import artifactor_plugin
from cfme.fixtures.soft_assert import _soft_assert_cm
from cfme.fixtures.soft_assert import SoftAssertionError


pytest_plugins = 'pytester'
# Tests in this module are a little bit weird, since soft_assert hooks in to pytest's call phase.
# The only way to actually test the call phase hook is to run pytest inside pytest using
# the pytester plugin.

test_file = """
pytest_plugins = [
    'cfme.fixtures.artifactor_plugin',
    'cfme.fixtures.soft_assert',
]


def test_soft_assert(soft_assert):
    soft_assert(None)
    soft_assert(False, 'soft_assert message!')
"""

test_output_match_lines = [
    ">*raise SoftAssertionError(_thread_locals.caught_asserts)",
    "E*SoftAssertionError: ",
    "E*soft_assert(None) ({testfile}:*)",
    "E*soft_assert message! ({testfile}:*)",
]


def test_soft_assert_call_hook(testdir, monkeypatch):
    monkeypatch.setattr(artifactor_plugin, 'UNDER_TEST', True)
    # create and run the pytest
    pyfile = testdir.makepyfile(test_file)
    result = testdir.runpytest_subprocess('--dummy-appliance')
    # replace the testfile name in the expected output names,
    # then check filename and lineno are correct in the failure output
    result.stdout.fnmatch_lines(
        [s.format(testfile=pyfile)
        for s in test_output_match_lines]
    )
    testdir.finalize()


def test_soft_assert_cm(soft_assert):
    with pytest.raises(AssertionError) as exc:
        # Run the soft assert context manager by itself to make sure it's
        # working right
        with _soft_assert_cm():
            soft_assert(None)
            soft_assert(False, 'Value is False')
            soft_assert(True, 'Value is True')

    # the AssertionError is related to soft assertions
    assert isinstance(exc.value, SoftAssertionError)

    # the number of failed assertions is what we expect
    assert len(exc.value.failed_assertions) == 2

    exc_message = str(exc.value)
    # showing code context instead of the message where appropriate
    assert 'soft_assert(None)' in exc_message

    # showing the message when it's passed in
    assert 'Value is False' in exc_message

    # assertions that pass aren't reported
    assert 'Value is True' not in exc_message

    # assertions are cleared if soft_assert is used twice in a test
    with _soft_assert_cm():
        # if assertions aren't cleared, this will erroneously raise AssertionError
        pass


def test_soft_assert_helpers(soft_assert):
    # catch_assert turns asserts into soft asserts
    with pytest.raises(AssertionError):
        with _soft_assert_cm():
            with soft_assert.catch_assert():
                assert False, 'message'

            with soft_assert.catch_assert():
                assert False is None

    # get the caught asserts; there are two of them
    caught_asserts = soft_assert.caught_asserts()
    assert len(caught_asserts) == 2

    # clear the asserts
    # also has the side-effect/benefit of preventing the call hook from failing this test
    soft_assert.clear_asserts()

    # the caught_asserts identifier is now empty after calling clear_asserts
    assert not caught_asserts


@pytest.fixture(scope="function")
def some_fixture(soft_assert):
    soft_assert(False, "bla bla bla")


@pytest.mark.xfail(raises=SoftAssertionError)
def test_soft_assert_fail_in_fixture(some_fixture):
    pass
