import time
from collections import namedtuple
from utils.log import logger
from functools import partial
from threading import Timer


WaitForResult = namedtuple("WaitForResult", ["out", "duration"])


def wait_for(func, func_args=[], func_kwargs={}, **kwargs):
    """Waits for a certain amount of time for an action to complete

    Designed to wait for a certain length of time,
    either linearly in 1 second steps, or exponentially, up to a maximum.
    Returns the output from the function once it completes successfully,
    along with the time taken to complete the command.

    Note: If using the expo keyword, the returned elapsed time will be inaccurate
        as wait_for does not know the exact time that the function returned
        correctly, only that it returned correctly at last check.

    Args:
        func: A function to be run
        func_args: A list of function arguments to be passed to func
        func_kwargs: A dict of function keyword arguments to be passed to func
        num_sec: An int describing the number of seconds to wait before timing out.
        expo: A boolean flag toggling exponential delay growth.
        message: A string containing a description of func's operation. If None,
            defaults to the function's name.
        fail_condition: An object describing the failure condition that should be tested
            against the output of func. If func() == fail_condition, wait_for continues
            to wait. Can be a callable which takes the result and returns boolean whether to fail.
            You can also specify it as a  set, that way it checks whether it is present in the
            iterable.
        handle_exception: A boolean controlling the handling of excepetions during func()
            invocation. If set to True, in cases where func() results in an exception,
            clobber the exception and treat it as a fail_condition.
        delay: An integer describing the number of seconds to delay before trying func()
            again.
        fail_func: A function to be run after every unsuccessful attempt to run func()
        quiet: Do not write time report to the log (default False)
        silent_failure: Even if the entire attempt times out, don't throw a exception.

    Returns:
        A tuple containing the output from func() and a float detailing the total wait time.

    Raises:
        TimedOutError: If num_sec is exceeded after an unsuccessful func() invocation.

    """
    st_time = time.time()
    total_time = 0
    num_sec = kwargs.get('num_sec', 120)
    expo = kwargs.get('expo', False)
    message = kwargs.get('message', None)

    if isinstance(func, partial):
        line_no = "<partial>"
        filename = "<partial>"
        if not message:
            params = ", ".join([str(arg) for arg in func.args])
            message = "partial function %s(%s)" % (func.func.func_name, params)
    else:
        line_no = func.func_code.co_firstlineno
        filename = func.func_code.co_filename
        if not message:
            message = "function %s()" % func.func_name

    fail_condition = kwargs.get('fail_condition', False)

    if callable(fail_condition):
        fail_condition_check = fail_condition
    elif isinstance(fail_condition, set):
        fail_condition_check = lambda result: result in fail_condition
    else:
        fail_condition_check = lambda result: result == fail_condition
    handle_exception = kwargs.get('handle_exception', False)
    delay = kwargs.get('delay', 1)
    fail_func = kwargs.get('fail_func', None)
    quiet = kwargs.get("quiet", False)
    silent_fail = kwargs.get("silent_failure", False)

    t_delta = 0
    logger.trace('Started {} at {}'.format(message, st_time))
    while t_delta <= num_sec:
        try:
            out = func(*func_args, **func_kwargs)
        except:
            if handle_exception:
                out = fail_condition
            else:
                raise
        if out is fail_condition or fail_condition_check(out):
            time.sleep(delay)
            total_time += delay
            if expo:
                delay *= 2
            if fail_func:
                fail_func()
        else:
            duration = time.time() - st_time
            if not quiet:
                logger.trace('Took {:0.2f} to do {}'.format(duration, message))
            logger.trace('Finished {} at {}'.format(message, st_time + t_delta))
            return WaitForResult(out, duration)
        t_delta = time.time() - st_time
    logger.trace('Finished at {}'.format(st_time + t_delta))
    if not silent_fail:
        logger.error('Could not complete {} at {}:{} in time, took {:0.2f}'.format(message,
            filename, line_no, t_delta))
        logger.error('The last result of the call was: {}'.format(str(out)))
        raise TimedOutError("Could not do {} at {}:{} in time".format(message, filename, line_no))
    else:
        logger.warning("Could not do {} at {}:{} in time but ignoring".format(message,
            filename, line_no))
        logger.warning('The last result of the call was: {}'.format(str(out)))


class TimedOutError(Exception):
    pass


class RefreshTimer(object):
    """
    Simple Timer class using threads.

    Initialized with a refresh period, a callback and args. Very similar to the
    actual threading.Timer class, when no callback function is passed, reverts to
    even simpler usage of just telling if a certain amount of time has passed.

    Can be resued.
    """

    def __init__(self, time_for_refresh=300, callback=None, *args, **kwargs):
        self.callback = callback or self.it_is_time
        self.time_for_refresh = time_for_refresh
        self.args = args
        self.kwargs = kwargs
        self._is_it_time = False
        self.start()

    def start(self):
        t = Timer(self.time_for_refresh, self.callback, self.args, self.kwargs)
        t.start()

    def it_is_time(self):
        self._is_it_time = True

    def reset(self):
        self._is_it_time = False
        self.start()

    def is_it_time(self):
        if self._is_it_time:
            return True
        else:
            return False
