"""
utils.wait
----------
"""
import time
from utils.log import logger


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
            to wait.
        handle_exception: A boolean controlling the handling of excepetions during func()
            invocation. If set to True, in cases where func() results in an exception,
            clobber the exception and treat it as a fail_condition.
        delay: An integer describing the number of seconds to delay before trying func()
            again.
        fail_func: A function to be run after every unsuccessful attempt to run func()

    Returns:
        A tuple containing the output from func() and a float detailing the total wait time.

    Raises:
        TimedOutError: If num_sec is exceeded after an unsuccessful func() invocation.

    """
    st_time = time.time()
    total_time = 0
    num_sec = kwargs.get('num_sec', 120)
    expo = kwargs.get('expo', False)
    message = kwargs.get('message', func.func_name)
    fail_condition = kwargs.get('fail_condition', False)
    handle_exception = kwargs.get('handle_exception', False)
    delay = kwargs.get('delay', 1)
    fail_func = kwargs.get('fail_func', None)

    t_delta = 0
    while t_delta <= num_sec:
        try:
            out = func(*func_args, **func_kwargs)
        except:
            if handle_exception:
                out = fail_condition
            else:
                raise
        if out == fail_condition:
            if fail_func:
                fail_func()
            time.sleep(delay)
            total_time += delay
            if expo:
                delay *= 2
        else:
            duration = time.time() - st_time
            logger.info('Took %f to do %s' % (duration, message))
            return out, duration
        t_delta = time.time() - st_time
    raise TimedOutError("Could not do %s in time" % message)


class TimedOutError(Exception):
    pass
