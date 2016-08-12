"""Handles errors based on something beyond the type.  You can match
error messages with regular expressions.  You can also extend the
matching behavior however you like.  By default, strings are treated
as regex and matched against the message of the error.  Functions are
passed the error and if the function returns 'truthy', then the error
is caught.


Usage:

    import utils.error as error
    with error.expected('foo'):
        x = 1
        raise Exception('oh noes foo happened!')  # this will be caught because regex matches

    with error.expected('foo'):
        raise Exception('oh noes bar happened!')  # this will bubble up because it doesn't match

    with error.expected('foo'):
        pass  # an error will be thrown because we expected an error but there wasn't one.

"""

from __future__ import unicode_literals
from contextlib import contextmanager
import re
from multimethods import singledispatch
from collections import Callable


@singledispatch
def match(o, e):
    """Returns true if the object matches the exception."""
    raise NotImplementedError("Don't know how to match {} to an error".format(type(o)))


@match.method(type)
def _exception(cls_e, e):
    """Simulates normal except: clauses by matching the exception type"""
    return isinstance(e, cls_e)


@match.method(Callable)
def _callable(f, e):
    """Pass the exception to the callable, if the callable returns truthy,
    then it's a match."""
    return f(e)


def regex(expr, e):
    """Search the message of the exception using the regex expr"""
    p = re.compile(expr)
    return p.search(str(e))


@match.method(basestring)
def _str(s, e):
    """Treat string as a regex and match it against the Exception's
    message."""
    return regex(s, e)


class UnexpectedSuccessException(Exception):
    """An error that is thrown when something we expected to fail didn't
    fail."""
    pass


@contextmanager
def handler(f):
    """Handles errors based on more than just their type.  Any matching
    error will be caught, the rest will be allowed to propagate up the
    stack."""
    try:
        yield
    except Exception as e:
        if not match(f, e):
            raise e


@contextmanager
def expected(f):
    """Inverts error handling.  If the enclosed block doesn't raise an
    error, it will raise one.  If it raises a matching error, it will
    return normally.  If it raises a non-matching error, that error
    will be allowed to propagate up the stack.

    """
    try:
        yield
        raise UnexpectedSuccessException(
            "Expected error matching '{}' but got success instead.".format(f))
    except UnexpectedSuccessException:
        raise
    except Exception as e:
        if not match(f, e):
            raise e
