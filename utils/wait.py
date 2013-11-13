'''
Created on Nov 11, 2013

@author: psavage

wait_for function, designed to wait for a certain length of time,
either linearly in 1 second steps, or exponentially, up to a maximum.
Returns the output from the function once it completes successfully,
along with the time taken to complete the command.

** Warning **
If using the expo keyword, the returned elapsed time will be inaccurate
as wait_for does not know the exact time that the function returned
correctly, only that it returned correctly at last check
'''

import time


def wait_for(func, func_args=[], func_kwargs={}, **kwargs):
    st_time = time.time()
    wait_time = 1
    total_time = 0
    num_sec = kwargs.get('num_sec', 120)
    expo = kwargs.get('expo', False)
    message = kwargs.get('message', func.func_name)
    fail_condition = kwargs.get('fail_condition', False)
    handle_exception = kwargs.get('handle_exception', False)

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
            time.sleep(wait_time)
            total_time += wait_time
            if expo:
                wait_time *= 2
        else:
            return out, time.time() - st_time
        t_delta = time.time() - st_time
    raise TimedOutError("Could not do %s in time" % message)


class TimedOutError(Exception):
    pass
