"""Soft assert context manager and assert function

A "soft assert" is an assertion that, if it fails, does not fail the entire test.
Soft assertions can be mixed with normal assertions as needed, and will be automatically
collected/reported after a test runs.

Functionality Overview
----------------------

1. If :py:func:`soft_assert` is used by a test, that test's call phase is wrapped in
   a context manager. Entering that context sets up a thread-local store for failed assertions.
2. Inside the test, :py:func:`soft_assert` is a function with access to the thread-local store
   of failed assertions, allowing it to store failed assertions during a test run.
3. After a test runs, the context manager wrapping the test's call phase exits, which inspects the
   thread-local store of failed assertions, raising a
   :py:class:`custom AssertionError <SoftAssertionError>` if any are found.

No effort is made to clear the thread-local store; rather it's explicitly overwritten with an empty
list by the context manager. Because the store is a :py:func:`list <python:list>`, failed assertions
will be reported in the order that they failed.

"""
from contextlib import contextmanager
from threading import local
from functools import partial

import fauxfactory
import pytest

from fixtures.artifactor_plugin import art_client
from utils.log import nth_frame_info
from utils.path import get_rel_path
import sys
import traceback
import utils

# Use a thread-local store for failed soft asserts, making it thread-safe
# in parallel testing and shared among the functions in this module.
_thread_locals = local()


@pytest.mark.hookwrapper
def pytest_runtest_call(item):
    """pytest hook to handle :py:func:`soft_assert` fixture usage"""
    # If a test is using soft_assert, wrap it in the context manager
    # This ensures SoftAssertionError will be raised in the call phase.
    if 'soft_assert' in item.fixturenames:
        with _soft_assert_cm():
            yield
    else:
        yield


class SoftAssertionError(AssertionError):
    """exception class containing failed assertions

    Functions like :py:class:`AssertionError <python:exceptions.AssertionError>`, but
    also stores the failed soft exceptions that it represents in order to properly
    display them when cast as :py:func:`str <python:str>`

    Args:
        failed_assertions: List of collected assertion failure messages
        where: Where the SoftAssert context was entered, can be omitted

    Attributes:
        failed_assertions: ``failed_assertions`` handed to the initializer,
            useful in cases where inspecting the failed soft assertions is desired.

    """
    def __init__(self, failed_assertions):
        self.failed_assertions = failed_assertions
        super(SoftAssertionError, self).__init__(str(self))

    def __str__(self):
        failmsgs = ['']

        for failed_assert in self.failed_assertions:
            failmsgs.append(failed_assert)
        return '\n'.join(failmsgs)


@contextmanager
def _soft_assert_cm():
    """soft assert context manager

    * clears the thread-local caught asserts before a test run
    * inspects the thread-local caught asserts after a test run, raising an error if needed

    """
    _thread_locals.caught_asserts = []
    yield _thread_locals.caught_asserts
    if _thread_locals.caught_asserts:
        raise SoftAssertionError(_thread_locals.caught_asserts)


def handle_assert_artifacts(request, fail_message=None):
    test_name = request.node.location[2]
    test_location = request.node.location[0]

    if not fail_message:
        short_tb = '%s' % (sys.exc_info()[1])
        full_tb = "".join(traceback.format_tb(sys.exc_info()[2]))
        full_tb = full_tb.encode('base64')

    else:
        short_tb = full_tb = fail_message.encode('base64')

    try:
        ss = utils.browser.browser().get_screenshot_as_base64()
        ss_error = None
    except Exception as b_ex:
        ss = None
        if b_ex.message:
            ss_error = '%s: %s' % (type(b_ex).__name__, b_ex.message)
        else:
            ss_error = type(b_ex).__name__
    if ss_error:
        ss_error = ss_error.encode('base64')

    # A simple id to match the artifacts together
    sa_id = "softassert-{}".format(fauxfactory.gen_alpha(length=3).upper())

    art_client.fire_hook('filedump', test_location=test_location, test_name=test_name,
        description="Soft Assert Traceback", contents=full_tb,
        file_type="soft_traceback", display_type="danger", display_glyph="align-justify",
        contents_base64=True, group_id=sa_id)
    art_client.fire_hook('filedump', test_location=test_location, test_name=test_name,
        description="Soft Assert Short Traceback", contents=short_tb,
        file_type="soft_short_tb", display_type="danger", display_glyph="align-justify",
        contents_base64=True, group_id=sa_id)
    if ss is not None:
        art_client.fire_hook('filedump', test_location=test_location, test_name=test_name,
            description="Soft Assert Exception screenshot",
            file_type="screenshot", mode="wb", contents_base64=True, contents=ss,
            display_glyph="camera", group_id=sa_id)
    if ss_error is not None:
        art_client.fire_hook('filedump', test_location=test_location, test_name=test_name,
            description="Soft Assert Screenshot error", mode="w",
            contents_base64=True, contents=ss_error, display_type="danger", group_id=sa_id)


@contextmanager
def _catch_assert_cm(request):
    """assert catching context manager

    * Catches a single AssertionError, and turns it into a soft assert

    """
    try:
        yield
    except AssertionError as ex:

        handle_assert_artifacts(request)

        caught_assert = _annotate_failure(str(ex))
        _thread_locals.caught_asserts.append(caught_assert)


# Some helper functions for creating or interacting with the caught asserts
def _get_caught_asserts():
    return _thread_locals.caught_asserts


def _clear_caught_asserts():
    # delete all items of the caught_asserts list
    del _thread_locals.caught_asserts[:]


def _annotate_failure(fail_message=''):
    # frames
    # 0: call to nth_frame_info
    # 1: _annotate_failure (this function)
    # 2: _annotate_failure caller (soft assert func or CM)
    # 3: failed assertion
    frameinfo = nth_frame_info(3)
    if not fail_message:
        fail_message = str(frameinfo.code_context[0]).strip()

    filename = get_rel_path(frameinfo.filename)
    path = '%s:%r' % (filename, frameinfo.lineno)
    return '%s (%s)' % (fail_message, path)


@pytest.fixture
def soft_assert(request):
    """soft assert fixture, used to defer AssertionError to the end of a test run

    Usage:

        # contents of test_soft_assert.py, for example
        def test_uses_soft_assert(soft_assert):
            soft_assert(True)
            soft_assert(False, 'failure message')

            # soft_assert.catch_assert will intercept AssertionError
            # and turn it into a soft assert
            with soft_assert.catch_assert():
                assert None

            # Soft asserts can be cleared at any point within a test:
            soft_assert.clear_asserts()

            # If more in-depth interaction is desired with the caught_asserts, the list of failure
            # messages can be retrieved. This will return the directly mutable caught_asserts list:
            caught_asserts = soft_assert.caught_asserts()

    The test above will report two soft assertion failures, with the following message::

        SoftAssertionError:
        failure message (test_soft_assert.py:3)
        soft_assert(None) (test_soft_assert.py:8)

    """
    def soft_assert_func(expr, fail_message=''):
        if not expr:
            handle_assert_artifacts(request, fail_message=fail_message)
            caught_assert = _annotate_failure(fail_message)
            _thread_locals.caught_asserts.append(caught_assert)
    # stash helper functions on soft_assert for easy access
    soft_assert_func.catch_assert = partial(_catch_assert_cm, request)
    soft_assert_func.caught_asserts = _get_caught_asserts
    soft_assert_func.clear_asserts = _clear_caught_asserts
    return soft_assert_func
