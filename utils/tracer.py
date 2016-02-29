"""
To use the function tracer, simply import the trace object and wrap a function with it

from utils.tracer import trace::

  @trace(scope=3)
  def func():
      print("something")

"""
import sys
from utils.log import logger
from functools32 import wraps


class FileStore(object):
    def __init__(self):
        """Simple file cacher

        A file store object is simple a cache of the file so that it doesn't have
        to be read each time. the __getitem__ function simple checks to see if the file is
        already present in the cache, if it is it serves it, if not it caches the file or
        returns a blank list if the file could not be read.
        """
        self._store = {}

    def __getitem__(self, name):
        if name in self._store:
            return self._store[name]
        else:
            try:
                self._store[name] = open(name, "r").readlines()
                return self._store[name]
            except IOError:
                return []


file_store = FileStore()


def trace(scope=1):
    """ Very simple tracer for functions and tests

    The tracer module is a very simple tracer that prints out lines of code as they are
    executed. It is useful when debugging tests so that you can actually see the lines of
    code being executed and hence determine where blocks are happening. This is not a
    substitute for good logging but a simple enhancement.

    Args:
        scope: This determines the depth of nested functions to go down, defaults to 1
    """
    frames = []

    def globaltrace(frame, why, arg):
        if frame.f_code.co_filename.endswith("tracer.py"):
            return globaltrace
        if why == "line":
            # line execution event
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno - 1
            try:
                padding = " " * (len(str(len(file_store[filename]))) - len(str(lineno)))
                line = file_store[filename][lineno].strip("\n")
            except IndexError:
                line = ""
            if len(frames) <= scope:
                logger.trace("{}:{}{} {}".format(len(frames), frame.f_lineno, padding, line))
        if why == "call":
            frames.append(frame)
            if len(frames) <= scope:
                s = "-" * len(frames)
                c = ">" * len(frames)
                logger.trace("{}{} call".format(s, c))
        if why == "return":
            if len(frames) <= scope:
                s = "-" * len(frames)
                c = "<" * len(frames)
                logger.trace("{}{} call".format(s, c))
            frames.pop()
        return globaltrace

    # def wrap(func):
    #    def _f(func, *args, **kwds):
    #        sys.settrace(globaltrace)
    #        result = func(*args, **kwds)
    #        sys.settrace(None)
    #        return result
    #    return decorator(_f)(func)
    # return wrap

    def wrap(func):
        @wraps(func)
        def _f(*args, **kwds):
            sys.settrace(globaltrace)
            result = func(*args, **kwds)
            sys.settrace(None)
            return result
        return _f
    return wrap
